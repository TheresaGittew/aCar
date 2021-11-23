import pandas as pd
import itertools
# Todo: Dynamic Range Adaption

A = [1,2,3,4]
B = ['Z', 'X', 'Y']

res = itertools.product(A, B)

for r in res:
    print (r[1])

# x_results = {(0,0,0):1, (1,1,1):2,(1,1,3):3 }
#
# keys = x_results.keys()
# origin_nodes = [i[0] for i in keys]
# destination_nodes = [i[1] for i in keys]
# days = [i[2] for i in keys]
#
# df_new_x = pd.DataFrame({'Origin': origin_nodes, 'Destination': destination_nodes, 'days':days})
#
#
# df_new_x['Result'] = pd.Series(list(zip(df_new_x.Origin, df_new_x.Destination, df_new_x.days))).map(x_results)
# print(df_new_x)

import numpy as np
a = np.zeros((4,2))
vals = [4,3,2,1]
pos = [(0,0),(1,1),(2,0),(3,1)]
rows, cols = zip(*pos)
print(rows)
a[rows, cols] = vals
print(a)


# Takes output objects from Gurobi Optimizer (as they are), converts into pd Dataframe and writes them into an excel sheet
def process_results(x, y, z, objVal, locs, days, fileName='10_24_DataGIS_1', ):
    writer = pd.ExcelWriter('Results/Output_' + fileName + '_Obj_val:' + str(objVal) + '.xlsx', engine='xlsxwriter')

    df = pd.DataFrame.from_dict(x, orient='index').reset_index()
    df.columns = ['Network', 'value']
    df.value = df.value.apply(lambda x: x.X)

    # X
    origins = [k[0] for k in x.keys()]
    destinations = [k[1] for k in x.keys()]
    days = [k[2] for k in x.keys()]
    df_x_ = pd.DataFrame({'Origin': origins, 'Destination': destinations, 'Days': days})
    df_x_['Value'] = pd.Series(list(zip(df_x_.Origin, df_x_.Destination, df_x_.Days))).map(x)
    df_x_.Value = df_x_.Value.apply(lambda u: u.x)
    pd.set_option('display.max_columns', None)
    df_x_.to_excel(writer, sheet_name='X_Results')

    # Y
    locations = [k[0] for k in y.keys()]
    days = [k[1] for k in y.keys()]
    df_y_ = pd.DataFrame({'Location': locations, 'Days': days})
    df_y_['Value'] = pd.Series(list(zip(df_y_.Location, df_y_.Days))).map(y)
    df_y_.Value = df_y_.Value.apply(lambda u: u.x)
    pd.set_option('display.max_columns', None)
    df_y_.to_excel(writer, sheet_name='Y_Results')

    # Z
    settlements = [k[0] for k in z.keys()]
    services = [k[1] for k in z.keys()]
    days = [k[2] for k in z.keys()]
    df_z_ = pd.DataFrame({'Settlement': settlements, 'Services': services, 'Days': days})
    df_z_['Value'] = pd.Series(list(zip(df_z_.Settlement, df_z_.Services, df_z_.Days))).map(z)

    df_z_.Value = df_z_.Value.apply(lambda u: u.x)
    pd.set_option('display.max_columns', None)
    df_z_.to_excel(writer, sheet_name='Z_Results')

    # Etc

    # Close the Pandas Excel writer and output the Excel file.
    writer.save()


def prep_output(self):
    self.res_y = np.ndarray((len(self.sets.T), len(self.sets.A)))
    self.res_l = np.ndarray((len(self.sets.T), len(self.sets.A)))
    self.res_q = np.ndarray((len(self.sets.T), len(self.sets.C), len(self.sets.S)))
    self.res_z = np.ndarray((len(self.sets.T), len(self.sets.C), len(self.sets.S)))
    self.res_z_hub = np.array([self.z_hub[0, t] for t in self.sets.T])

    for t in range(len(self.sets.T)):
        for a in range(len(self.sets.A)):
            i, j = self.sets.A[a]
            self.res_y[t, a] = self.y[i, j, t].x
            # self.res_l[t, a] = round(self.l[i,j,t].x)

        for i in range(len(self.sets.C)):
            for s in range(len(self.sets.S)):
                self.res_q[t, i, s] = round(self.q[self.sets.C[i], t, self.sets.S[s]].x)
                self.res_z[t, i, s] = self.z[self.sets.C[i], t, self.sets.S[s]].x

    for k, v in self.y.items():
        if v.x != 0:
            print(k, v.x)

    # self.result_times_arcs_list = np.array([[t, i, j,self.y[i, j, t].x] for (i, j) in self.sets.A for t in self.sets.T])
    # self.result_times_loads = np.array([[t, i, j,self.l[i, j, t].x] for (i, j) in self.sets.A for t in self.sets.T])
    # self.result_visited_nodes = np.array([[t, i ,self.z[i, t].x] for i in self.sets.C for t in self.sets.T])
    # self.starter_nodes =  np.array([[t, self.z_hub[0,t]] for t in self.sets.T])
    # self.qs = np.array([[t, i, self.q[i, t].x] for i in self.sets.C for t in self.sets.T])





