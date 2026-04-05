import matplotlib
matplotlib.use('Agg')
import os
import sys
import time
import random
import numpy as np
import networkx as nx
import logging
# for consistency between python2 and python3
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)
import dreamplace.configure as configure
import Params
import PlaceDB
import Timer
import NonLinearPlace
import pdb

from itertools import combinations
from collections import Counter
from networkx.algorithms.approximation import randomized_partitioning
from tqdm import tqdm
import matplotlib.pyplot as plt


def partition(params):
    """
    @brief Top API to run the partition.
    @param params parameters
    """

    assert (not params.gpu) or configure.compile_configurations["CUDA_FOUND"] == 'TRUE', \
            "CANNOT enable GPU without CUDA compiled"
    
    method = params.partition_params['method']
    iterations = params.partition_params['iterations']
    
    np.random.seed(params.random_seed)
    # read database
    tt = time.time()
    placedb = PlaceDB.PlaceDB()
    placedb(params)

    # construct graph
    start_time = time.time()
    G = graph_construction(placedb)
    print("Time consumed for graph construction: {}s".format(time.time() - start_time))
    # partitaion graph
    if params.partition_params['type'] == 3:
        # partition_result = graph_partition(G, iters=iterations, seed=params.random_seed, method=method, lam=params.partition_params['lam'])
        print(True)
    elif params.partition_params['type'] == 1:
        partition_result = graph_partition_mem_on_logic(G, seed=params.random_seed, method=method, lam=params.partition_params['lam'], SA_flag=False)
    elif params.partition_params['type'] == 2:
        partition_result = graph_partition_mem_on_logic(G, seed=params.random_seed, method=method, lam=params.partition_params['lam'], SA_flag=True)
    return partition_result

def total_area(G, cut):
    upper_area = 0.
    bot_area = 0.
    for node in cut:
        if not G.nodes[node]['is_macro']:
            upper_area += G.nodes[node]['area']
        else:
            upper_area += G.nodes[node]['area']

    for node in G.nodes - cut:
        if not G.nodes[node]['is_macro']:
            bot_area += G.nodes[node]['area']
        else:
            bot_area += G.nodes[node]['area']
    return {"upper_area": upper_area, "bot_area": bot_area}

def SA(G, current_cut, current_cut_size, areas, macros, seed=None, method='min_cut', lam=10):
    def mutation(cut, mutation_rate=0.1):
        new_cut = cut.copy()
        for i in range(len(new_cut)):
            if random.random() < mutation_rate:
                new_cut[i] = 1 - new_cut[i]
        return new_cut
    
    # initialization
    T = 1
    gamma = 0.9
    binary_cut = current_cut
    best_cut = current_cut[:]
    current_obj_1 = - current_cut_size if method == 'max_cut' else current_cut_size # min obj
    current_obj_2 = np.abs(areas['upper_area'] - areas['bot_area']) 
    current_obj = current_obj_1 + lam * current_obj_2
    best_obj_1 = current_obj_1
    best_obj_2 = current_obj_2
    best_obj = current_obj
    log_interval = 10
    i = 0
    print(best_cut)
    print("Cut size: {}, Area difference: {}, Upper-die area: {}, Bottom-die area: {} in iteration {}".format(best_obj_1, best_obj_2, areas["upper_area"], areas["bot_area"], i))
    # simulated annealing
    while T > 0.1:
        # mutation
        new_binary_cut = mutation(binary_cut)
        
        # compute the change of objective function
        new_cut_size = nx.algorithms.cut_size(G, macros[new_binary_cut])
        new_areas = total_area(G, macros[new_binary_cut])
        new_obj_1 = - new_cut_size if method == 'max_cut' else new_cut_size # min obj
        new_obj_2 = np.abs(new_areas['upper_area'] - new_areas['bot_area'])
        new_obj = new_obj_1 + lam * new_obj_2
        # print(new_binary_cut)
        # accept new solution
        obj_delta = new_obj - current_obj
        p = np.exp(-obj_delta / T)
        # print(obj_delta, new_obj_1, new_obj_2, new_obj)
        if obj_delta < 0 or (random.random() < p):
            binary_cut = new_binary_cut
            areas = new_areas
            current_obj_1 = new_obj_1
            current_obj_2 = new_obj_2
            current_obj = new_obj
            if new_obj < best_obj:
                best_obj = new_obj
                best_obj_1 = new_obj_1
                best_obj_2 = new_obj_2
                best_cut = new_binary_cut[:]
            
        T = T * gamma
        i += 1
        if i % log_interval == 0:
            # print(macros)
            print(best_cut)
            print("Cut size: {}, Area difference: {}, Upper-die area: {}, Bottom-die area: {} in iteration {}".format(best_obj_1, best_obj_2, areas["upper_area"], areas["bot_area"], i))
        
    return best_obj_1, areas, best_cut

def graph_construction(db):
    G = nx.MultiGraph()
    # G = nx.Graph()
    
    # nodes
    node_attrs = {}
    mean_node_area = 0.
    num = 0
    for node_name in db.node_names:
        node = db.node_name2id_map[node_name.decode('utf-8')]
        if node < (db.num_physical_nodes - db.num_terminal_NIs):  # exclude IO ports
            G.add_node(node)
            node_area = db.node_size_x[node] * db.node_size_y[node]
            node_attrs[node] = {"is_macro": False, 
                                "area": node_area,    # scale the area of cells
                                "name": node_name.decode('utf-8')}
            
            mean_node_area += node_area
            num += 1
            
    mean_node_area = mean_node_area / num
    # detect macros
    for node_name in db.node_names:
        node = db.node_name2id_map[node_name.decode('utf-8')]
        if node < (db.num_physical_nodes - db.num_terminal_NIs):  # exclude IO ports
            node_area = db.node_size_x[node] * db.node_size_y[node]
            if (node_area > (mean_node_area * 10)) and (db.node_size_y[node] > (db.row_height * 2)):
                node_attrs[node]["is_macro"] = True
                
    nx.set_node_attributes(G, node_attrs)

    # edges
    edges = []
    size = []
            
    for net_name in db.net_names:
        net = db.net_name2id_map[net_name.decode('utf-8')]
        pins = db.net2pin_map[net]
        connected_nodes = []
        size.append(len(pins))
        
        for pin in pins:
            if db.pin2node_map[pin] < (db.num_physical_nodes - db.num_terminal_NIs):  # exclude IO ports
                connected_nodes.append(db.pin2node_map[pin])
        if len(pins) < 10:
            edges.extend(combinations(connected_nodes, r=2))
    # plt.hist(size, bins=100)
    # plt.savefig('net_size.jpg', dpi=100)
    # edge_count = Counter(edges)
    # for edge in edge_count.keys():
    #     weight = edge_count[edge]
    #     G.add_edge(edge[0], edge[1], weight=weight)
    for edge in edges:
        G.add_edge(edge[0], edge[1])
    return G

# def cut_size_incre(G, initial_cut, node, if_swap=True):
#     '''
#     Compute the cut size in an incremental way. After changing the side of a node, remove the old cut edges and add new ones.
#     '''
#     cut_size_change = 0
#     upper_area_change = 0.
#     bot_area_change = 0.
#     for neighbor in G[node]:
#         if (neighbor in initial_cut) and (node in initial_cut):
#             cut_size_change += 1
#         if (neighbor not in initial_cut) and (node in initial_cut):
#             cut_size_change -= 1
#         if (neighbor in initial_cut) and (node not in initial_cut):
#             cut_size_change -= 1
#         if (neighbor not in initial_cut) and (node not in initial_cut):
#             cut_size_change += 1        
        
#     if node in initial_cut:
#         upper_area_change -= G.nodes[node]['area']
#         bot_area_change += G.nodes[node]['area']
#     else:
#         upper_area_change += G.nodes[node]['area']
#         bot_area_change -= G.nodes[node]['area']

#     return cut_size_change, upper_area_change, bot_area_change

# def one_exchange(G, current_cut, current_cut_size, areas, seed=None, method='min_cut', lam=10):
#     def _swap_node_partition(cut, node):
#         return cut - {node} if node in cut else cut.union({node})
#     cut = set(current_cut)
#     while True:
#         nodes = list(G.nodes())
#         # random select a node for exchange
#         random.shuffle(nodes)
#         random_node = nodes[0]
#         # find the best exchange
#         cut_size_change, upper_area_change, bot_area_change = cut_size_incre(G, cut, random_node)
#         cut_size_delta = cut_size_change if method == 'max_cut' else - cut_size_change
#         obj_delta = cut_size_delta + lam * (np.abs(areas['upper_area'] - areas['bot_area']) 
#                                              - np.abs(areas['upper_area'] + upper_area_change - (areas['bot_area'] + bot_area_change)))

#         if obj_delta > 0:
#             cut = _swap_node_partition(cut, random_node)
#             current_cut_size += cut_size_change
#             areas['upper_area'] = areas['upper_area'] + upper_area_change
#             areas['bot_area'] = areas['bot_area'] + bot_area_change
#             break

#     partition = cut
#     return current_cut_size, areas, partition

# def graph_partition(G, iters=10000, seed=2024, method='min_cut', lam=10):
#     # init solution
#     cut_size, partition = randomized_partitioning(G, seed)
#     partition = partition[0]
#     # local search
#     for _ in tqdm(range(iters)):
#         cut_size, partition = one_exchange(G, partition, seed, method=method, lam=lam)      

#     return partition

def graph_partition_mem_on_logic(G, seed=2024, method='min_cut', lam=10, SA_flag=True):
    # init solution
    macros = []
    for node in G.nodes:
        if G.nodes[node]['is_macro']:
            macros.append(node) 
    macros = np.array(macros)
    partition = np.ones(len(macros), dtype=np.bool)
    current_cut_size = nx.algorithms.cut_size(G, macros[partition])
    areas = total_area(G, macros[partition])
    if SA_flag:
        # simulated annealing
        cut_size, areas, partition = SA(G, partition, current_cut_size, areas, macros, seed, method=method, lam=lam)      
    
    upper_die_names = []
    for macro in macros[partition]:
        upper_die_names.append(G.nodes[macro]["name"])

    return G.nodes - macros[partition], upper_die_names
            

if __name__ == "__main__":
    """
    @brief main function to invoke the entire placement flow.
    """
    logging.root.name = 'DREAMPlace'
    logging.basicConfig(level=logging.INFO,
                        format='[%(levelname)-7s] %(name)s - %(message)s',
                        stream=sys.stdout)
    params = Params.Params()
    params.printWelcome()
    if len(sys.argv) == 1 or '-h' in sys.argv[1:] or '--help' in sys.argv[1:]:
        params.printHelp()
        exit()
    elif len(sys.argv) != 2:
        logging.error("One input parameters in json format in required")
        params.printHelp()
        exit()

    # load parameters
    params.load(sys.argv[1])
    logging.info("parameters = %s" % (params))
    # control numpy multithreading
    os.environ["OMP_NUM_THREADS"] = "%d" % (params.num_threads)

    # run placement
    tt = time.time()
    partition(params)
    logging.info("placement takes %.3f seconds" % (time.time() - tt))