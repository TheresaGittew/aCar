import pandas as pd
import xlsxwriter

import matplotlib.pyplot as plt
import os

def read_excel_row_for_given_vec_number (input_path):
    df = pd.read_excel(input_path)
    df.columns= ['LB_Range', 'UB_Range', 'ShareCustomer', 'NumVehicles', 'TotalDist']
    df_multi = df.set_index(['LB_Range', 'UB_Range', 'ShareCustomer', 'NumVehicles'])
    return df_multi


def plot_meta_result_per_vec_num(customer_shares_list, range_setting_list, results, vehicles, filename_output):
    print(range_setting_list)
    print(customer_shares_list)


    x_coordinates_of_bars = [i for i in range (len(customer_shares_list))]
    label_ticks = list(map(lambda x: str(x), range_setting_list))
    #plt.bar(x_coordinates_of_bars, results, width=0.9, tick_label=customer_shares_list)

    plt.figure(num=3, figsize=(10, 7.5))

    colors = iter(['C1','C2','C0','C4','C5'])
    style = iter(['--','-','-.',':','--'])
    tickstyle = iter([4,5,6,7,1,0])

    i = 0
    for v in vehicles:
        elem = next(colors)
        linestyle = next(style)
        tick = next(tickstyle)
        plt.plot(customer_shares_list, results[v], color=elem, marker=tick, linestyle=linestyle, linewidth='1.5', label='# vehicles: '+str(v), alpha=1-i)
        i += 0.008


    # ticks + grid
    plt.minorticks_on()
    plt.grid(True, axis='x', which='minor', alpha=0.3)
    plt.grid(True, axis='y', which='minor', alpha=0.3)
    plt.grid(True, axis='y', which='major', alpha=0.8)
    plt.grid(True, axis='x', which='major', alpha=0.8)

    plt.xlabel('Covered Population')
    plt.ylabel('Total transportation distance in 60 days')

    plt.legend(loc='best')

    # save results
    plot_dir = os.path.dirname(__file__)
    results_dir = os.path.join(plot_dir,
                               'Results/')
    sample_plot_name = filename_output


    if not os.path.isdir(results_dir):
        os.makedirs(results_dir)

    # plt.gca().invert_xaxis()

    plt.savefig(results_dir + sample_plot_name)
    plt.clf()





def create_plots_for_vehicles(vehicles, filepath_to_read, filename_output):
    pd_df = read_excel_row_for_given_vec_number(filepath_to_read)


    results_list = {}
    for v in vehicles:
        tiny_df = pd_df.loc[(slice(None), slice(None), slice(None), v),:]  # retrieves the relevant part of pd dataframe for that customer
        results = list(map(lambda x: None if x == '-' else x, tiny_df['TotalDist']))
        results_list[v] = results

    list_range_values_lb  = list(map(lambda x: str(x),tiny_df.index.get_level_values(0)))
    list_range_values_ub = list(map(lambda x: str(x),tiny_df.index.get_level_values(1)))
    list_share_cust_vals = list(tiny_df.index.get_level_values(2))

    plot_meta_result_per_vec_num(customer_shares_list=list_share_cust_vals,
                                 range_setting_list=list_range_values_ub,
                                 results=results_list, vehicles=vehicles, filename_output=filename_output)




def paint_output(VRP_obj, dataframes, path):
    # # add arcs_list to plot
    active_times_arcs_list = dict(
        (t, (i, j)) for (i, j) in VRP_obj.sets.A for t in VRP_obj.sets.T if VRP_obj.y[i, j, t].x > 0.99)

    # plot result for each time slot
    for t in VRP_obj.sets.T:
        xc = VRP_obj.sets.coordinates[0]
        yc = VRP_obj.sets.coordinates[1]
        y_results = dataframes['y']
        q_results = dataframes['q']
        l_results = dataframes['l']

        plt.figure(figsize=(12, 8), dpi=80)
        # # plot the hub
        hub, = plt.plot(VRP_obj.sets.coordinates[0][0], VRP_obj.sets.coordinates[1][0], c='r', marker='s', label='Hub')
        # # plot the clients (highlight in green if not all considered)
        all_customers = plt.scatter(xc[1:], yc[1:], c='grey', alpha=0.5, label='Customer')
        workaround_q, = plt.plot([], [], ' ', label="q: Number of provided Services")

        # plot active customers
        active_x_coordinates = [xc[i] for i in VRP_obj.sets.C]
        active_y_coordinates = [yc[i] for i in VRP_obj.sets.C]

        active_customers = plt.scatter(active_x_coordinates, active_y_coordinates, c='g', label='Active Customers')

        # plot used arcs (y == 1):
        for a in range(len(VRP_obj.sets.A)):
            i, j = VRP_obj.sets.A[a]

            if int(y_results.loc[(i,j,t),:].item()) > 0.5:
                plt.plot([xc[i], xc[j]], [yc[i], yc[j]], c='b', alpha=0.6)

                # retrieve load
                load = round(float(l_results.loc[(i, j, t, 'PNC'), :].item()))
                if i != 0:
                    x_coor = min (xc[i], xc[j]) + abs(xc[i] - xc[j])/2 + 0.03
                    y_coor = min (yc[i], yc[j]) + abs(yc[i] - yc[j])/2
                    plt.text(x_coor, y_coor, s='l : ' + str(load), c='b', alpha=0.9)

        # plot number of services
        for c in range(len(VRP_obj.sets.C)):

            q_value = round(float(q_results.loc[(VRP_obj.sets.C[c],t, 'PNC'),:].item()))

            if q_value != 0:
                plt.text(xc[VRP_obj.sets.C[c]] + 0.03, yc[VRP_obj.sets.C[c]], s='q: ' + str(q_value))

            plt.text(xc[VRP_obj.sets.C[c]]+0.005, yc[VRP_obj.sets.C[c]], s='C ' + str(VRP_obj.sets.C[c]),
                     c='green')

        plt.xlabel('xcoord (long.)')
        plt.ylabel('ycoord (lat.)')
        plt.legend(handles=[all_customers, active_customers, hub, workaround_q])

        plot_dir = os.path.dirname(__file__)
        results_dir = os.path.join(plot_dir, path+ '/Scenario_limit-'+str(VRP_obj.sets.limit)+'vehicle-'+str(VRP_obj.sets.K)+'/')
        sample_plot_name = "Plot_VRP_" + str(t)



        if not os.path.isdir(results_dir):
            os.makedirs(results_dir)

        #plt.gca().invert_xaxis()
        plt.savefig(results_dir  + sample_plot_name)
        plt.clf()
