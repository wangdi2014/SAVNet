#! /usr/bin/env python

try:
    import cPickle as pickle
except:
    import pickle


import random
from collections import namedtuple
from network import Network

Link_info_mut = namedtuple("Link_info_mut", ("Mutation_Key", "Motif_Pos", "Mutation_Type", "Is_Canonical", "Splicing_Key", "Splicing_Class", "Is_Inframe"))


def get_mut_sample_info(mut_info, mut2sample):
    mut_infos = mut_info.split(',')
    tchr, tstart, tend, tref, talt = mut_infos[0], mut_infos[1], mut_infos[1], mut_infos[2], mut_infos[3]
    # deletion
    if len(tref) > 1:
        tref = tref[1:]
        talt = "-"
        tstart = str(int(tstart) + 1)
        tend = str(int(tstart) + len(tref) - 1)
    if len(talt) > 1:
        tref = "-"
        talt = talt[1:]

    mut = '\t'.join([tchr, tstart, tend, tref, talt])
    return(mut2sample[mut])


def create_network_list(merged_candidate_link_list, network_pickles_file, mut2sample_file, sample_list, weight_vector, sv_mode = False):

    # may need to fix when savnet is modified to accept vcf format file
    mut2sample = {}
    if sv_mode == False:
        with open(mut2sample_file, 'r') as hin:
            for line in hin:
                F = line.rstrip('\n').split('\t')
                mut = '\t'.join(F[0:5])
                mut2sample[mut] = [int(x) - 1 for x in F[5].split(',')]
    else:
        with open(mut2sample_file, 'r') as hin:
            for line in hin:
                F = line.rstrip('\n').split('\t')
                mut = ','.join(F[0:7])
                mut2sample[mut] = [int(x) - 1 for x in F[7].split(',')]


    out_s = open(network_pickles_file, 'wb')
    with open(merged_candidate_link_list, 'r') as hin:

        header2ind = {}
        header = hin.readline().rstrip('\n').split('\t')
        for i in range(len(header)):
            header2ind[header[i]] = i


        temp_gene = ""
        temp_mutation_status = {}
        temp_splicing_counts = []
        temp_link2info = {}
        
        temp_mut_id = 0
        temp_mutation_key2id = {}
        temp_splicing_id = 0 
        temp_splicing_key2id = {}

        for line in hin:

            F = line.rstrip('\n').split('\t')

            if F[header2ind["Gene_Symbol"]] != temp_gene:
                if temp_gene != "":
                    # flush the result
                    network = Network(temp_gene, temp_mutation_status, temp_splicing_counts, temp_link2info, sample_list, weight_vector)    
                    pickle.dump(Network(temp_gene, temp_mutation_status, temp_splicing_counts, temp_link2info, sample_list, weight_vector), out_s)

                temp_gene = F[header2ind["Gene_Symbol"]]
                temp_mutation_status = {}
                temp_splicing_counts = []
                temp_link2info = {}

                temp_mut_id = 0
                temp_mutation_key2id = {}
                temp_splicing_id = 0
                temp_splicing_key2id = {}
    
            # get mutation id and splicing id
            mutation_key = F[header2ind["Mutation_Key"]]
            if mutation_key not in temp_mutation_key2id:
                temp_mutation_key2id[mutation_key] = temp_mut_id
                temp_mutation_status[temp_mut_id] =  get_mut_sample_info(mutation_key, mut2sample)
                temp_mut_id = temp_mut_id + 1

            splicing_key = F[header2ind["Splicing_Key"]]
            if splicing_key not in temp_splicing_key2id:
                temp_splicing_key2id[splicing_key] = temp_splicing_id
                temp_splicing_counts.append([int(x) for x in F[header2ind["Read_Counts"]].split(',')])
                temp_splicing_id = temp_splicing_id + 1


            link = (temp_mutation_key2id[mutation_key], temp_splicing_key2id[splicing_key])

            ###
            # This procedure is for mutation. Procedure for SV is also required
            mutation_key = F[header2ind["Mutation_Key"]]
            motif_pos = F[header2ind["Motif_Pos"]]
            mutation_type = F[header2ind["Mutation_Type"]]
            is_canonical = F[header2ind["Is_Canonical"]]
            splicing_class = F[header2ind["Splicing_Class"]]
            is_inframe = F[header2ind["Is_Inframe"]]

            temp_link2info[link] = Link_info_mut(mutation_key, motif_pos, mutation_type, is_canonical, splicing_key, splicing_class, is_inframe)
            ###


            ###
            # Is this necessary?
            """
            # consider the case where one mutation is both disrupting and creating splicing motifs
            if temp_mut2id[mut] + '\t' + temp_splicing2id[splicing_key] in temp_ids2link_info:
                # disrupting annotations are preferentially added to link info
                if F[header2ind["Mutation_Type"]] in ["splicing donor disruption", "splicing acceptor disruption"]:
                    temp_ids2link_info[temp_mut2id[mut] + '\t' + temp_splicing2id[splicing_key]] = link_info
                elif F[header2ind["Mutation_Type"]] in ["splicing donor creation", "splicing acceptor creation"] and \
                    "splicing branchpoint disruption" in temp_ids2link_info[temp_mut2id[mut] + '\t' + temp_splicing2id[splicing_key]]:
                    temp_ids2link_info[temp_mut2id[mut] + '\t' + temp_splicing2id[splicing_key]] = link_info
                # prefer canonical splicing branchpoint disruption rather than non-canonical splicing branchpoint disruption
                elif F[header2ind["Mutation_Type"]] == "splicing branchpoint disruption" and \
                    "splicing branchpoint disruption" in temp_ids2link_info[temp_mut2id[mut] + '\t' + temp_splicing2id[splicing_key]] and \
                    F[header2ind["Is_Canonical"]] == "canonical":
                    temp_ids2link_info[temp_mut2id[mut] + '\t' + temp_splicing2id[splicing_key]] = link_info
q            else:
                temp_ids2link_info[temp_mut2id[mut] + '\t' + temp_splicing2id[splicing_key]] = link_info
            """
            ###


    # flush the result
    if temp_gene != "":
        pickle.dump(Network(temp_gene, temp_mutation_status, temp_splicing_counts, temp_link2info, sample_list, weight_vector), out_s)

    out_s.close()



def execute_savnet(network_pickles_file, sample_list, permutation_num):


    sample_num = len(sample_list)
    sav_list_target = []
    logBF_values_target = []

    in_s = open(network_pickles_file, 'rb')
    while True:
        try:
            network = pickle.load(in_s)
            network.prune_link_vector(3.0)
            network.cluster_link_vector()
            network.get_averaged_bayes_factors(1.0, 1.0, 1.0, 0.01)

            for sav in network.export_to_savs(3.0):
                sav_list_target.append(sav)
                logBF_values_target.append(sav.score)

        except EOFError:
            break


    logBF_values_null = []
    sav_lists_permutation = []
    for i in range(permutation_num):
        temp_sav_list = []

        seed = range(sample_num)
        no_overlap = 0
        while no_overlap == 0:
           random.shuffle(seed)
           overlap_num = sum([seed[i] == i for i in range(sample_num)])
           if overlap_num == 0: no_overlap = 1

        print seed
        in_s = open(network_pickles_file, 'rb')
        while True:
            try:
                network = pickle.load(in_s)
                network.execute_permutation(seed)
                network.prune_link_vector(3.0)
                network.cluster_link_vector()
                network.get_averaged_bayes_factors(1.0, 1.0, 1.0, 0.01)
    
                for sav in network.export_to_savs(3.0):
                    temp_sav_list.append(sav)
                    logBF_values_null.append(sav.score)

            except EOFError:
                break

        sav_lists_permutation.append(temp_sav_list)



    logBF2FPR = {}
    for logBF in logBF_values_target:
        null_num_est = float(len([x for x in logBF_values_null if x >= logBF])) / permutation_num
        nonnull_num = float(len([x for x in logBF_values_target if x >= logBF]))
        pFPR = null_num_est / nonnull_num if nonnull_num > 0.0 else 0.0
        logBF2FPR[logBF] = pFPR
 
    logBF2qvalue = {}
    temp_min_FPR = float("inf")
    for logBF in sorted(logBF2FPR, key = float):
        if logBF2FPR[logBF] <= temp_min_FPR:
            temp_min_FPR = logBF2FPR[logBF]
        logBF2qvalue[logBF] = temp_min_FPR


    for sav in sav_list_target:
        sav.set_fdr(logBF2qvalue[sav.score])
        print sav.print_records()


if __name__ == "__main__":

    import sys

    sample_list = ["A427", "A549", "ABC-1", "H1299", "H1437", "H1648", "H1650", "H1703", "H1819", 
                   "H1975", "H2126", "H2228", "H2347", "H322", "II-18", "LC2_ad", "PC-14", "PC-3", 
                   "PC-7", "PC-9", "RERF-LC-Ad1", "RERF-LC-Ad2", "RERF-LC-KJ", "RERF-LC-MS", "RERF-LC-OK", "VMRC-LCD"]

    weight_vector = [5.2935, 2.5843, 4.6718, 6.7032, 6.3449, 4.8819, 3.2902, 11.6925, 9.7603, 4.4712, 5.8023, 7.3304, 6.6022,
                     6.8118, 8.0286, 5.5164, 6.7205, 6.3547, 6.5036, 4.2754, 6.989, 5.63, 7.514, 6.6156, 4.1002, 6.0268]

    create_network_list(sys.argv[1], sys.argv[2], sys.argv[3], sample_list, weight_vector)

    execute_savnet(sys.argv[2], sample_list, 100)



