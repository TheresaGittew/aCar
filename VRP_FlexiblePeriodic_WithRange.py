import numpy as np
import matplotlib.pyplot as plt
from gurobipy import Model, GRB, quicksum
from VRP_AuxFunctions import service_provision_update_range, link_used_update_battery, update_battery_usage
from ReadNilsInputFiles import read_demands, read_odmatrix, read_coors, find_relevant_customers, find_max_number_vehicles
from PreparationOutput import prepare_outputs, analyze_results
from PlotOutput import paint_output

from enum import Enum
class Variant(Enum):
     DEFAULT = 1
     MIN_TOTAL_NUMBER_OF_SERVICE = 2
     DYNAMIC_ACAR_RANGE = 3

class FP_VRP_Input():

    # Parameter information
    # customer_list: [1, ...n] list with indices of n customers (settlement) which also, together with the hub (index 0), make up the nodes
    # services_list [0, .. v] list of service indices
    # time_intervals_list:  list[0,1, ...m] list with time interval indices, where one time interval corresponds to for example 1 day
    # demands_total_dict: nested dictionary where the 'first layer key' is a settlement (customer), and the second layer key is a type of service

    # demand_maxperinterval_dict = following the same concept like demands_total_dict, provides the max. amount a settlement takes per day
    # arcs_list: list of tuples, where (m,n) is a link between customer (node) m and customer (node) n
    # distances: dictionary where key is an arc a and value is a tuple, where the first value is the time distance and second is the total distance in km
    # coordinates: x,y coordinates of hub and customers (settlements)
    # service duration: dictionary that contains for each service index an info about setup-time and service time

    # vehicle_capa (?) => Here: sufficiently large value
    # Service duration: Dictionary where you can look up the type of service (index) and ['setup_time'] or to obtain the time needed to provide service


    def __init__(self, vehicle_props, customer_list, services_list, timeintervals_list, demands_total_dict, demand_maxperinterval_dict,
                 arcs_list, distances, coordinates, vehicle_capa, number_vehicles, service_info, a_car_range, limit,
                 hours_per_day, variant='Default', v_s=None):
        self.variant = variant
        self.vehicle_props = vehicle_props
        self.C = customer_list          # customers
        self.S = services_list          # services
        self.T = timeintervals_list     # list of timeintervals
        self.N = [0] + self.C           #
        self.A = list(arcs_list)              # arcs

        self.W_i = demands_total_dict
        self.w_i = demand_maxperinterval_dict

        self.vehicle_capa = vehicle_capa
        self.car_range = a_car_range
        self.K = number_vehicles
        self.c = dict(((i, j), distances [i, j][1]) for i, j in self.A) # distances (km) per arc
        self.d = dict(((i,j), distances [i,j][0]) for i, j in self.A) # travel time per arc

        self.coordinates = coordinates
        self.service_info = service_info
        self.time_budget_p_day = hours_per_day
        self.a_car_range = a_car_range
        self.limit = limit

        self.v_s = v_s # Variant of the problem in which only a minimum number of services is provided

        if self.variant == Variant.DYNAMIC_ACAR_RANGE:
            self.create_potential_max_ranges_for_od_matrix()

    def create_potential_max_ranges_for_od_matrix(self):

        self.arc_weight_to_battery_usage \
            = dict(((i,j, m),(m, (self.c[(i,j)] / self.vehicle_props.compute_range_for_weight(m)))) for (i,j) in self.A for m in range(self.vehicle_props.max_weight+1))
        self.weight_steps = [i for i in range(0, self.vehicle_props.max_weight+1) if i % 10 == 0]



class MIP_FP_VRP():
    # model set up
    def __init__(self, vrp_inputs):
        self.sets = vrp_inputs
        self.mp = Model('FP_VRP')

        # setting up the decision variables
        self.y = self.mp.addVars(vrp_inputs.A, vrp_inputs.T, vtype=GRB.BINARY)                  # whether link is taken or not
        self.z = self.mp.addVars(vrp_inputs.C, vrp_inputs.T, vrp_inputs.S , vtype=GRB.BINARY)   # whether customer is visited in time t or not for service s
        self.z_hub = self.mp.addVars([0], vrp_inputs.T, lb=0, vtype=GRB.INTEGER)             # hub decision variable
        self.q = self.mp.addVars(vrp_inputs.C, vrp_inputs.T, vrp_inputs.S, lb=0, vtype=GRB.INTEGER) # number of services provided at a location
        self.l = self.mp.addVars(vrp_inputs.A, vrp_inputs.T, vrp_inputs.S, lb=0, vtype=GRB.INTEGER) # because vehicle capacity itself is not sth we analyze (for now)

        # new variables
        self.b = self.mp.addVars(vrp_inputs.N, vrp_inputs.T , lb=0, vtype=GRB.CONTINUOUS)  # verbleibende Stunden je Tour
        self.r = self.mp.addVars(vrp_inputs.N, vrp_inputs.T, lb=0, vtype=GRB.CONTINUOUS)  # verbleibende Gesamtstrecke je Tour

        if self.sets.variant == Variant.MIN_TOTAL_NUMBER_OF_SERVICE:
            self.W_var = self.mp.addVars(vrp_inputs.C, vrp_inputs.S, lb=0, vtype=GRB.INTEGER)

        if self.sets.variant == Variant.DYNAMIC_ACAR_RANGE:
            self.e = self.mp.addVars(vrp_inputs.N, vrp_inputs.T, lb=0, vtype=GRB.CONTINUOUS) # verbleibnde Batterieladung je Tour
            self.helper_e = self.mp.addVars(vrp_inputs.A, vrp_inputs.T, vrp_inputs.weight_steps,
                                     vtype=GRB.BINARY)  # Load total
    def set_objective(self):
        self.mp.modelSense = GRB.MINIMIZE

        # here, you can potentially add further cost factors
        self.mp.setObjective(quicksum(self.y[i, j, t] * self.sets.c[i, j] for (i, j) in self.sets.A for t in self.sets.T))

    def set_constraints(self):


        # constraint 2: number of services (q) provided ad t for customer i should not exceed the maximum demand per day
        self.mp.addConstrs(self.q[i, t, s] <= self.sets.w_i[i][s] * self.z[i, t, s]
                           for t in self.sets.T
                           for i in self.sets.C
                           for s in self.sets.S)

        # constraint 3 - total load (for all services) provided on one tour (to all customers) should not be alrger than vehicle capacities of all vehicles
        # important: if constraint 6 and 7 from the original formulation are not used, the vehicle capacity should be used like a big M)
        self.mp.addConstrs\
            (quicksum(self.q[i,t, s] for i in self.sets.C for s in self.sets.S) <= self.sets.vehicle_capa * self.z_hub[0, t] for t in self.sets.T)

        # constraint 4 => connect z's and y's (there have to be an outgoing link in case a node is visited, e.g. z turns to 1) # todo: why can't we take incoming links?
        self.mp.addConstrs(
            quicksum(self.y[i, j, t] for j in self.sets.N if (i, j) in self.sets.A) == self.z[i, t, s] for t in
            self.sets.T for i in self.sets.C for s in self.sets.S)

        # constraint 5 : flow continuity
        self.mp.addConstrs(
            quicksum(self.y[i, j, t] for j in self.sets.N if (i, j) in self.sets.A) == quicksum(self.y[j, i, t] for j in self.sets.N if (j,i) in self.sets.A) for t in
            self.sets.T for i in self.sets.N)

        # constraint 6 :
        # case one: i != 0 => i is a customer
        self.mp.addConstrs(quicksum(self.l[i,j,t, s] for j in self.sets.N if (i,j) in self.sets.A)
                        - quicksum(self.l[j,i,t, s] for j in self.sets.N if (j,i) in self.sets.A) ==
                           - self.q[i,t, s] for i in self.sets.C for t in self.sets.T for s in self.sets.S)

        # case two: i == 0 => i is the hub
        self.mp.addConstrs(quicksum(self.l[i, j, t, s] for j in self.sets.N
                                    if (i, j) in self.sets.A)  - quicksum(self.l[j, i, t, s]
                                                                          for j in self.sets.N if (j, i) in self.sets.A) == quicksum(self.q[i_2,t, s] for i_2 in self.sets.C)
                          for i in [self.sets.N[0]] for t in self.sets.T for s in self.sets.S)

        # constraint 7: load on each arch must not exceed the vehicle capacity
        self.mp.addConstrs(quicksum(self.l[i,j,t, s]  for s in self.sets.S) <= self.sets.vehicle_capa * self.y[i,j,t] for (i,j) in self.sets.A for t in self.sets.T)

        # constraint 8: respect number of available vehicles
        self.mp.addConstrs(quicksum(self.y[0,j,t] for j in self.sets.N if (0,j) in self.sets.A) <= self.sets.K for t in self.sets.T)

        # constraint 9: connect y and z_hub, so that the initial, outgoing y's have to turn to 1 in case z_hub is > 0 (see also ocnstraint 3)
        self.mp.addConstrs(self.z_hub[0,t] == quicksum(self.y[0,i, t] for i in self.sets.C) for t in self.sets.T)

        # constraint 10: connect q and g
        if self.sets.variant == Variant.MIN_TOTAL_NUMBER_OF_SERVICE:
            self.mp.addConstrs(quicksum(self.q[i, t, s] for t in self.sets.T) >= self.W_var[i, s] for i in self.sets.C for s in
                self.sets.S)
            self.mp.addConstrs(self.W_var[i, s]  <= self.sets.W_i[i][s] for i in self.sets.C for s in
                self.sets.S)
            self.mp.addConstrs(quicksum(self.W_var[i, s] for i in self.sets.C) >= self.sets.v_s[s] for s in self.sets.S)
        else:
            self.mp.addConstrs(quicksum(self.q[i, t, s] for t in self.sets.T)
                               == self.sets.W_i[i][ s] for i in self.sets.C for s in self.sets.S)
        # Todo: Idea: Hier könnte man die Anzahl der T's auch so anpassen, dass abhängig vom Typen kleinere Sets von T gewählt werden

        # constraint 11: time constraints
        # self.mp.addConstrs(quicksum(self.z[i, t, s] * self.sets.service_info[s]['setup_time'] + self.q[i,t,s]
        #                             * self.sets.service_info[s]['service_time']
        #                             for s in self.sets.S for i in self.sets.C)
        #                    + quicksum(self.y[i,j,t] * self.sets.d[i,j] for (i,j) in self.sets.A) <= self.sets.time_budget_p_day * self.z_hub[0,t] for t in self.sets.T)


        # Fall 1 : alle "inneren" Kanten werden berücksichtigt, d.h. weder Origin noch Destination ist 0 (Hub)
        self.mp.addConstrs((1 - self.y[i,j,t] ) * 1000 + self.b[i, t]
                                - self.sets.d[i,j]  - quicksum(self.z[j, t, s] * self.sets.service_info[s]['setup_time'] for s in self.sets.S)
                                - quicksum(self.q[ j, t, s] * self.sets.service_info[s]['service_time'] for s in self.sets.S)
                           >= self.b[j, t] for i in self.sets.C for j in self.sets.C if (i,j) in self.sets.A for t in self.sets.T)
                        # Beachte: hier durch self.sets.C loopen, da damit der Hub automatisch ausgeschlossen wird.

        # Fall 2: der Ausgangsknoten ist 0, jeder Destinationknoten ist in C.
        self.mp.addConstrs((1 - self.y[i,j,t] ) * 1000 + self.sets.time_budget_p_day - self.sets.d[i,j]
                           - quicksum(self.z[j, t, s] * self.sets.service_info[s]['setup_time'] for s in self.sets.S)
                           - quicksum(self.q[j, t, s] * self.sets.service_info[s]['service_time'] for s in self.sets.S)
                           >= self.b[j, t] for i in [0] for j in self.sets.C if (i,j) in self.sets.A for t in self.sets.T)
                        # Beachte: hier durch self.sets.C für alle Destinations loopen, da damit der Hub automatisch ausgeschlossen wird.

        # Fall 3: der Ausgangsknoten ist ein Customer, der Zielknoten ist 0
        self.mp.addConstrs((1 - self.y[i, j, t]) * 1000 + self.b[i, t] - self.sets.d[i, j]
                           >= self.b[j, t] for i in self.sets.C for j in [0] if (i, j) in self.sets.A for t in
                           self.sets.T)

        self.mp.addConstrs(self.b[i, t] >= 0.001 for i in self.sets.C for t in self.sets.T)

        # aCar Range (Genau dasselbe wie oben, nur für die zurückgelegte Strecke)
        self.mp.addConstrs((1 - self.y[i, j, t]) * 1000 + self.r[i, t] - self.sets.c[i, j]
                           >= self.r[j, t] for i in self.sets.C for j in self.sets.N if (i, j) in self.sets.A for t in
                           self.sets.T)

        self.mp.addConstrs((1 - self.y[i, j, t]) * 1000 + self.sets.car_range - self.sets.c[i, j]
                           >= self.r[j, t] for i in [0] for j in self.sets.C if (i, j) in self.sets.A for t in
                           self.sets.T)

        if self.sets.variant == Variant.DYNAMIC_ACAR_RANGE:
            self.add_dynamic_acar_constraints()


    def add_dynamic_acar_constraints(self):
        print("Battery usage" , self.sets.arc_weight_to_battery_usage)


        self.mp.addConstrs(
            quicksum(self.helper_e[i,j, t, w] * self.sets.arc_weight_to_battery_usage[i,j, w][0] for w in self.sets.weight_steps) == quicksum(self.l[i,j, t, s] * self.sets.service_info[s]['weight_pu'] for s in self.sets.S)
            for (i,j) in self.sets.A if j!= 0
            for t in self.sets.T ) # for all links except last one

        self.mp.addConstrs(
            self.helper_e[i, j, t, w] >= self.y[i,j,t] for w in [0] for (i, j) in self.sets.A for t in self.sets.T if j == 0)  # for link back to hub

        self.mp.addConstrs( quicksum(self.helper_e[i,j, t, w] for w in self.sets.weight_steps) <= 1  for i,j in self.sets.A for t in self.sets.T)

        self.mp.addConstrs(
            (1 - self.y[i, j, t]) * 1000 + 100 - self.helper_e[i, j, t, w] * self.sets.arc_weight_to_battery_usage[i,j,w][1] * 100 >= self.e[j, t]
            for i in [0] for j in self.sets.C if (i, j) in self.sets.A
            for t in self.sets.T for w in self.sets.weight_steps)

        self.mp.addConstrs(
            (1 - self.y[i, j, t]) * 1000 + self.e[i, t] - self.helper_e[i,j,t,w] *  self.sets.arc_weight_to_battery_usage[
                i, j, w][1] * 100 >= self.e[j, t]
            for i in self.sets.C for j in self.sets.N if (i, j) in self.sets.A
            for t in self.sets.T for w in self.sets.weight_steps)



    def solve_model(self):
        self.mp.Params.MIPGap = 0.001
        # self.mp.setParam('OutputFlag', 0)
        self.mp.optimize()

        if self.sets.variant == Variant.DYNAMIC_ACAR_RANGE:
            print("These are the selected weights transported on an arc:")
            print("arc(o-d), time, weight   |   Value ")
            for k, v in self.helper_e.items():

                if v.X != 0:
                    print (k ,  v)

            print("This is the remaining battery status per node ")
            print("node, time              |battery status")
            for k, v in self.e.items():

                print(k, v)





    def prep_output(self, path_for_output):
        if self.mp.Status == 3 or self.mp.Status == 4:
            self.status_sol = 'INF_OR_UNBD'

        else:
            self.df_outputs = prepare_outputs([0], [self.z, self.q, self.y, self.l,  self.z_hub], [['customer_index', 'time_index', 'service_type'],
                                                                    ['customer_index', 'time_index', 'service_type'],
                                                                    ['i', 'j', 'time_index',
                                                                     ], ['i', 'j', 'time_index',
                                                                     'service_type'], ['node_index', 'time_index']], ['z','q','y','l', 'z_hub'], exel_file_path=path_for_output)
            self.status_sol = 'SUCCESS'



