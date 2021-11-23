import csv
import numpy as np

# Hand over the filename (including the path)
# Important: Currently we still have the workaround to check if the second column element is int or not.
# Thats how we ignore possible headers.

# IMPORTANT: Removes arcs from node to the same node

def read_odmatrix(filename):

    def convert_comma (string):
        return string.replace(",",".")

    with open (filename, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        od = {}
        for rows in reader:
            origin = int(rows[1])
            destination = int(rows[2])
            travel_time = float(convert_comma(rows[3]))
            distance =   float(convert_comma(rows[4]))
            if origin != destination:
                od[(origin,destination)] = travel_time, distance

    csvfile.close()
    #  Important: (0,0)-arcs have been filtered out!
    return od


def convert_comma (string):
    return string.replace(",",".")

# Die demands müssen so angegeben werden, dass demand_type_names eine Liste von Namen übergeben bekommt
# Diese Liste von Namen sind die Codenamen für die einzelnen Services, z.B. ['PNC', 'VACC', ... ]
# Wichtig: Die Reihenfolge der Codenames muss der Reihenfolge der aufgeführten Demands im .csv file entsprechen
# Factors maximum daily sets the proportion of the total demand of the entire planning horizon
# which can be fulfilled per day

def read_demands(filepath, demand_type_names, factors_maximum_daily):
    services_dict = {}
    services_maximum_daily_dict = {}
    with open (filepath, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter =';')
        for rows in reader:
            services_dict[(int(rows[0]))] = dict((demand_type_names[d], float(convert_comma(rows[d+1]))) for d in range(0, len(demand_type_names)))
            services_maximum_daily_dict[(int(rows[0]))] = dict((demand_type_names[d], factors_maximum_daily[d] * float(convert_comma(rows[d+1]))) for d in range(0, len(demand_type_names)))
    return services_dict, services_maximum_daily_dict


def read_service_times(filepath):
    service_times_dict = {}
    with open (filepath, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter =';')
        for rows in reader:
            service_times_dict[rows[0]] = {}
            service_times_dict[rows[0]]['setup_time'] = rows[1]
            service_times_dict[rows[0]]['service_time'] = rows[2]
            service_times_dict[rows[0]]['weight_pu'] = rows[3]

    return service_times_dict


# parameter filename: includes path
def read_coors(filename):
    coordinates_dict_x = []
    coordinates_dict_y = []
    with open (filename, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter =';')
        for rows in reader:
            coordinates_dict_x.append(float(convert_comma(rows[1])))
            coordinates_dict_y.append(float(convert_comma(rows[2])))
    return coordinates_dict_x, coordinates_dict_y


def find_relevant_customers(arcs_list, number_customers, min_distance_bekoji, max_distance_bekoji):
    lis = [c for c in range(1,number_customers+1) if arcs_list[0,c][1] > min_distance_bekoji and arcs_list[0,c][1] < max_distance_bekoji]
    return lis


def find_max_number_vehicles(number_customers, length_time_horizon, service_times, services_dict, services_maximum_daily_dict, od_matrix):
    total_visits = 0
    for i in range(1, number_customers+1):
        # variante 1: the max. demand limits the number of provided services p.d.
        min_number_visits_according_to_max_demand = int(np.ceil(services_dict[i]['PNC'] / services_maximum_daily_dict[i]['PNC']))

        # variante 2: the service time limits the number of provided services p.d.
        number_allowed_services_according_to_service_time = ((8 - service_times['PNC']['setup_time'] - 2* od_matrix[0,i][0]) / service_times['PNC']['service_time'])
        min_number_visits_according_to_service_time = int(np.ceil(services_dict[i]['PNC'] / number_allowed_services_according_to_service_time))

        # which is constraining
        max_visits_per_horizon = max(min_number_visits_according_to_max_demand, min_number_visits_according_to_service_time)


        total_visits += max_visits_per_horizon

    return np.ceil(total_visits / length_time_horizon)

