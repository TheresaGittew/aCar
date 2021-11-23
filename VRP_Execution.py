from VRP_FlexiblePeriodic_WithRange import FP_VRP_Input, MIP_FP_VRP, Variant
from ReadNilsInputFiles import read_odmatrix, read_coors, read_demands, find_relevant_customers, find_max_number_vehicles, read_service_times
from PlotOutput import paint_output
from VRP_AuxFunctions import VehicleFeatures

import xlsxwriter
import itertools

# # # #Todo
# # Specify path for input files
path_demand_file = 'GIS_Data/11-19-21_EXAMPLE_DemandList2.csv'
path_OD_matrix= 'GIS_Data/11-19-21_EXAMPLE_ODs.csv'
path_service_times = 'GIS_Data/11-19-21_EXAMPLE_ServiceTimes.csv'
v_features_2 = VehicleFeatures(range_zero_weight=200, range_1000kgs_weight=50, total_capa=1000, max_weight=500)

# # User sets number of customers
# # # # #
customer_number = 26
timeintervals_number = 2
services = ['PNC']
a_Car_range = 1000
time_per_day = 100
factor_max_daily = 1
v_s = {'PNC':120}

# # # #Todo
# # User sets scenarios (total number of needed vehilces, ub and lb distance)
# # #
number_vec = [2]
distance_limits_ub = [40]
distance_limits_lb = [30]
path_for_outputs = 'Results/Results-11-21-Min_Nr_Services/'

# # # Todo
# select variant (see enum in VRP_FlexiblePeriodic.py)
variante = Variant.MIN_TOTAL_NUMBER_OF_SERVICE




# # # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
total_demands_nested_dict, daily_max_demand_nested_dict = read_demands(path_demand_file, demand_type_names=['PNC'], factors_maximum_daily=[factor_max_daily])

# coordinates
coordinates = read_coors('GIS_Data/11-15-21_CoordinatesLongitudeLatitude.csv')

# service duration
services_times = read_service_times (path_service_times)

# vehicle capacity
vehicle_capacity = 40


metastudy_results = {}
scenarios = itertools.product(number_vec, distance_limits_lb, distance_limits_ub)

for s in scenarios:
    v_num = s[0]
    d_l_l = s[1]
    d_l_u = s[2]

    relevant_customers =  [6,9,10,17,18,22,4,1]     #find_relevant_customers(od_matrix_as_dict,len(customer_list), d_l_l, d_l_u)
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
                          variant=variante, v_s=v_s)

    model = MIP_FP_VRP(inputs)
    model.set_constraints()
    model.set_objective()
    model.solve_model()
    model.prep_output() # output is prepared, check with model.status_sol to see if feasible
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
