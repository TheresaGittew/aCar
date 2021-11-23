import pandas as pd
import numpy as np


# col_names_list has to go from left to the right; important: one has to be value! Otherwise throws error
def dict_to_pd_dataframe(dict, col_names_list):
    df = pd.DataFrame.from_dict(dict, orient='index')
    df.index = pd.MultiIndex.from_tuples(list(dict.keys()), names=(col_names_list))
    df.columns = ['value']
    df.value = df.value.apply(lambda x: x.X)
    return df


def prepare_outputs(input_sets, list_of_output_dicts, list_of_col_names, output_pd_names, excel_file_name='Results/Output_FH_VRP_new.xlsx'):
    writer = pd.ExcelWriter(excel_file_name, engine='xlsxwriter')

    output_dicts = {}
    for l in range(len(list_of_output_dicts)):
        print(list_of_col_names[l])
        output_dicts[output_pd_names[l]] = dict_to_pd_dataframe(list_of_output_dicts[l], list_of_col_names[l])
        pd.set_option('display.max_columns', None)
        output_dicts[output_pd_names[l]].to_excel(writer, sheet_name=output_pd_names[l])

    writer.save()

    # print(output_dicts['z'].loc[(slice(None),1,'PNC'),:])
    return output_dicts

def analyze_results(pd_dataframes, od_matrix, set):
    y_dict = pd_dataframes['y']
    total_distance = 0
    for t in set.T:
        dataseries = y_dict.loc[(slice(None), slice(None), t),:]
        print("\n Current day : " , t)
        relevant_indices = dataseries.value[dataseries.value == 1].index.tolist()
        relevant_arcs = list(map(lambda tup : (tup[0], tup[1]), relevant_indices))
        distance_today = sum(list(map(lambda tup: od_matrix[tup][1], relevant_arcs)))
        print("Used Arcs are: " , relevant_arcs)
        print("Distance Today is: " , distance_today)
        total_distance += distance_today
    print("total distance: ", total_distance)

