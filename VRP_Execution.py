from VRP_FlexiblePeriodic_WithRange import FP_VRP_Input, MIP_FP_VRP, Variant
from ReadNilsInputFiles import read_odmatrix, read_coors, read_demands, find_relevant_customers, find_max_number_vehicles, read_service_times
from PlotOutput import paint_output
from VRP_AuxFunctions import VehicleFeatures

import xlsxwriter
import itertools

# Variante: Variant.DEFAULT
# Beispiel: Von allen 26 Siedlungen werden von Anfang nur 8 angeschaut: [6,9,10,17,18,22,4,1]
#           Von diesen 8 sind die Demands gegeben (siehe EXAMPLE_DemandList.csv)
#           You could either set hours to 8 (which would constrain the routes) and aCar to 1000
#           Or hours to 50 and aCar to 100
#
#           - - - - - - -
#           aCar_range = 1000 (should important here)
#           time_per_day = 8
#           path_demand_file = 'GIS_Data/11-19-21_EXAMPLE_DemandList.csv'
#           path_OD_matrix= 'GIS_Data/11-19-21_EXAMPLE_ODs.csv'
#           path_service_times = 'GIS_Data/11-19-21_EXAMPLE_ServiceTimes.csv' - Also make sure that the service times are PNC;0.15;0.15;10
#           set variant: variante = Variant.DEFAULT

#           Also: set variable path_for_outputs to a new path to sth understandable


# Variante: Variant.MIN_TOTAL_NUMBER_OF_SERVICE
# Beispiel: Von allen 26 Siedlungen werden von Anfang nur 8 angeschaut: [6,9,10,17,18,22,4,1]
#           Von diesen 8 sind die Demands gegeben (siehe EXAMPLE_DemandList2.csv)
#           Für diesen Fall muss required_services_per_type gesetzt werden u. auf jeden Fall an die FP_VRP_INPUT(..) übergeben werden.
#           required_services_per_type determines the number of services that HAVE to be provided per type, so in case
#           the model wants to optimize travel distances OR has other limiting constraints (such as limited travel time),
#           its possible to not visit all settlements but only the ones that are required to meet the number of given required services per type.
#           In this example, we have the problem that 11-19-21-_EXAMPLE_ODs contains a larger total demand
#           Than, for example, the one that can be provided with 2 vehicles on 2 days with 8 available hours p.d.
#           Hence, this model picks those nodes for which the model is still feasible, while ensuring that min. 120 services
#           are provided:
#           - - - - - - -
#           aCar_range = 1000 (not important here)
#           time_per_day = 8
#           required_services_per_type = {'PNC':120}
#           path_demand_file = 'GIS_Data/11-19-21_EXAMPLE_DemandList2.csv'
#           path_OD_matrix= 'GIS_Data/11-19-21_EXAMPLE_ODs.csv'
#           path_service_times = 'GIS_Data/11-19-21_EXAMPLE_ServiceTimes.csv' - Also make sure that the service times are PNC;0.15;0.15;10
#           set variant: variante = Variant.MIN_TOTAL_NUMBER_OF_SERVICE


#  Variante 3: Variant.DYNAMIC_ACAR_RANGE
#           Auch hier werden nur [6,9,10,17,18,22,4,1] betrachtet; demands: 'GIS_Data/11-19-21_EXAMPLE_DemandList.csv'
#           Hier sind vehicle features wichtig, d.h. ein "VehicleFeatures" Objekt muss erstellt werden; dazu
#           braucht man die Parameter range_zero_weight (Reichweite aCar bei 0 Traglast), range_1000kg_weight (Reichtweite bei 100kg Gewicht),
#           Sowie MaximalGewicht und totale Kapazität (letzteres nicht zwangsläufig, hier erstmal dummy wert eintragen)
#           Also, make sure to provide the WEIGHT PER ITEM in the file which includes the service info (in a fourth column),
#           E.g. PNC;0.15;0.15;10, meaning that one item 'PNC' has a weight of 10kg
#           Then, the battery status is computed dynamically depending on the weight that traverses a particular arc
#           Todo: Remove aCar static range for this use case - until then: set aCar Range to a large value eg 1000


# Always: set variable path_for_outputs to a new path to sth understandable


# # # #Todo
# # Specify path for input files
path_demand_file = 'GIS_Data/11-19-21_EXAMPLE_DemandList.csv'
path_OD_matrix= 'GIS_Data/11-19-21_EXAMPLE_ODs.csv'
path_service_times = 'GIS_Data/11-19-21_EXAMPLE_ServiceTimes.csv'
coordinates = read_coors('GIS_Data/11-15-21_CoordinatesLongitudeLatitude.csv')      #  'GIS_Data/11-23-21-CoordinatesLongitudeLatitude.csv')

v_features_2 = VehicleFeatures(range_zero_weight=200, range_1000kgs_weight=50, total_capa=1000, max_weight=500)


# # User sets number of customers
# # # # #
customer_number = 26
timeintervals_number = 2
services = ['PNC'] #['WAT']
a_Car_range = 500

time_per_day = 8
factor_max_daily = 1   # factor that determines the max. amount a node can receive per day (share of total amount W_i)
required_services_per_type =    {'PNC':120} # {'WAT': 1000}


path_for_outputs = 'Results/Results-11-24-TEST/'


# # # #Todo
# # User sets scenarios (total number of needed vehilces, ub and lb distance)
# # #
number_vec = [2]
distance_limits_ub = [100] # range upper bound in km (distance to hub)
distance_limits_lb = [30] # range lower bound in km (distance to hub)

# # # Todo
# select variant (see enum in VRP_FlexiblePeriodic.py)
variante = Variant.DEFAULT


# # # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# #  Hier nichts ändern
# # # Basic index lists OD_Matrices_2_ET.csv
customer_list = [i for i in range(1,customer_number)]
services_list = services  # 1 service
list_timeintervals = [i for i in range(0, timeintervals_number)]

# arcs and their distances
od_matrix_as_dict = read_odmatrix(path_OD_matrix)    # returns a dictionary with arcs -> distances
arcs = od_matrix_as_dict.keys()

# demand data
# required input format: list with customers, and
data_name = services_list[0]
total_demands_nested_dict, daily_max_demand_nested_dict = read_demands(path_demand_file, demand_type_names=[data_name], factors_maximum_daily=[factor_max_daily])

# coordinates

# service duration
services_times = read_service_times (path_service_times)

# vehicle capacity
vehicle_capacity = 100


metastudy_results = {}

scenarios = itertools.product(number_vec, distance_limits_lb, distance_limits_ub)

for s in scenarios:
    v_num = s[0]
    d_l_l = s[1]
    d_l_u = s[2]

    relevant_customers =  [6,9,10,17,18,22,4,1]  # find_relevant_customers(od_matrix_as_dict,len(customer_list), d_l_l, d_l_u)  #  [6,9,10,17,18,22,4,1]
    customer_share = len(relevant_customers) / len(customer_list)


    # print(" + + + + + NEXT ITERATION + + + + + + \nNumber Vehicles:" , str(v_num), "Distance limit lower / upper:",str(d_l_l), "|", str(d_l_u))
    # print("Current customer list: " , relevant_customers, " |Customer share" , customer_share)

    inputs = FP_VRP_Input(vehicle_props=v_features_2, customer_list=relevant_customers,
                          services_list=services_list,
                          timeintervals_list=list_timeintervals,
                          demands_total_dict=total_demands_nested_dict,
                          demand_maxperinterval_dict=daily_max_demand_nested_dict,
                          arcs_list=arcs, distances=od_matrix_as_dict,
                          coordinates=coordinates, vehicle_capa=vehicle_capacity,
                          number_vehicles = v_num, service_info=services_times,
                          a_car_range=a_Car_range, limit=(d_l_l, d_l_u), hours_per_day=time_per_day,
                          variant=variante, v_s=required_services_per_type)

    model = MIP_FP_VRP(inputs)
    model.set_constraints()
    model.set_objective()
    model.solve_model()
    model.prep_output(path_for_outputs) # output is prepared, check with model.status_sol to see if feasible
    if model.status_sol == 'INF_OR_UNBD':  metastudy_results[d_l_l, d_l_u, customer_share, v_num] = '-'
    else:
        paint_output(model, model.df_outputs, path_for_outputs)
        metastudy_results[d_l_l, d_l_u,  customer_share, v_num] =  model.mp.objVal


# # #
# # Record Meta Results (Key findings for all scenarios, summarized in an excel sheet)
# # #
workbook = xlsxwriter.Workbook(path_for_outputs+'Results_Metastudy.xlsx')
worksheet = workbook.add_worksheet()
row = 0
col = 0
worksheet.write(row, col, 'Min. Distance')
worksheet.write(row, 1, 'Max. Distance')
worksheet.write(row, 2, 'Pop. Share')
worksheet.write(row, 3, '# Vehicles')
worksheet.write(row, 4, 'Total Distance')


for key in metastudy_results.keys():
    row += 1
    c = 0
    for k in key:
        worksheet.write(row, col + c, k)
        c += 1
    worksheet.write(row, col + c, metastudy_results[key])


workbook.close()
