class ServiceFeatures():
    def __init__(self, weight_per_unit):
        self.weight_p_u = weight_per_unit
        self.name= 'PNC'

class VehicleFeatures():


    def __init__(self, range_zero_weight, range_1000kgs_weight, total_capa, max_weight):
        self.range_max = range_zero_weight
        self.range_one_ton = range_1000kgs_weight
        self.slope = (self.range_one_ton - self.range_max) / 1000
        self.total_capa = total_capa
        self.max_weight = max_weight


    def compute_range_for_weight(self, weight_total):
        return (weight_total * self.slope + self.range_max)


def service_provision_update_range(vehicle_features, number_units, service, battery_status):
    range_full_battery = vehicle_features.compute_range_for_weight(number_units * service.weight_p_u)
    range_real = battery_status * range_full_battery
    return range_real, range_full_battery


def link_used_update_battery(range_full_battery_old, range_real, driven):
    range_real_dif = range_real - driven
    battery = range_real_dif / range_full_battery_old
    return battery


def update_battery_usage(vehicle_features, distance, load, service_weight):
    range_total = vehicle_features.compute_range_for_weight(load)
    battery_usage = distance / range_total
    return battery_usage


v_features_2 = VehicleFeatures(range_zero_weight=200, range_1000kgs_weight=50, total_capa=1000, max_weight=500)
print(v_features_2.compute_range_for_weight(150))