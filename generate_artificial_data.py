#/usr/bin/env python3
import pandas as pd
import numpy as np
import os
import json
import fire
from copy import deepcopy
from numpy import nan, random
import datetime

"""
call as: python3 generate_artificial_data.py

Create two tables of artificial data: one with one entry per (pm_id, date), another with one entry per pm_id.
There is one class to create one table each.
These tables are saved as csv-files (one per table).
These artificial data can then be used to validate the algorithm of "pairwise processing" and "aggregation of all datasets". The results can visualised as well.

read a config file: 
- provide the number of datasets
- read a matrix relating different datasets to each other for the pm_id table
- a similar matrix for the number of days 

- simulate project_member_id (and person_ids)

output:
per_day.csv-files for each dataset containing the correct number of overlapping days and people.


"""

class artificialDatasets():
    def __init__(self, config_filename : str, config_path : str):
        f = open(os.path.join(config_path, config_filename))
        # reading the IO_json config file
        IO_json = json.load(f)
        self.artificial_data = IO_json["artificial_data"]
        seed = self.artificial_data["seed"]
        if len(seed) == 0 or seed == "None":
            seed = None
        else:
            seed = int(seed)
        self.random = random.default_rng(seed)
        self.root_data_dir_name = IO_json["root_data_dir_name"]

        self.date_range = self.artificial_data["date_range"]
        self.matrix_pm_id = self.artificial_data["matrices"]["per_pm_id"]
        self.matrix_day = self.artificial_data["matrices"]["per_day"]
        self.output = IO_json["core"]["individual"]
        self.count_datasets = self.artificial_data["count_datasets"]
        self.IO_json = IO_json
        self.validate_config_file()

        # output, data to be generated
        self.days = [[]*self.count_datasets]  # this is for every entry (i,j) in the matrix
        self.df_days = []  # this is the list of dataframes, one for every entry (i,j)
        self.df_days_compiled = [] # dataframes, one per dataset (i)


    def __del__(self):
        # create output directories and write dataframes to disk
        for df, ds in zip(self.df_days_compiled,self.output):
            os.makedirs(os.path.join(self.root_data_dir_name, ds[0]), exist_ok=True)
            df.to_csv(os.path.join(self.root_data_dir_name, ds[0], ds[1]))
            print(f"outfiles created: {os.path.join(self.root_data_dir_name, ds[0], ds[1])}")

    def sim_pm_ids(self, i : int, j : int) -> tuple:
        """
        i,j are indicating a matrix element of self.matrix_pm_id and self.matrix_day, each representing a dataset
        it has already been asserted, that count_pm_ids >= count_days in validate_config_file()
        
        one tuple i,j represents a list of dates and persons that are present in both datasets i and j.
        The persons have separate project member ids in the two datasets.
        (If i==j then it is present in the single dataset i.)

        returns a tuple of arrays of length count_days for every given (i,j): 
            one representing indices of a persons, for which data is present at any given day
        """
        count_pm_ids = self.matrix_pm_id[i][j]
        count_days = self.matrix_day[i][j]
        # these represent the different project member ids in the two datasets for the same person
        pm_ids1 = self.random.integers(10000000,99999999, count_pm_ids)
        pm_ids2 = self.random.integers(10000000,99999999, count_pm_ids)

        # fill now the array of length count_days:
        # simulate first the list of person_id indices as an intermediate step to generate the project_m_ids below  
        # here we have only one 
        person_id_indices = self.random.integers(0, count_pm_ids, count_days)
        person_id_indices.sort()

        # simulate the project_member_ids, that a person has in the two datasets
        project_m_ids1, project_m_ids2 = [],[]
        for k in range(count_days):
            project_m_ids1.append(pm_ids1[person_id_indices[k]])
            project_m_ids2.append(pm_ids2[person_id_indices[k]])

        return project_m_ids1, project_m_ids2, person_id_indices

    def sim_dates(self, i : int, j : int, person_id_indices : list) -> list:
        """
        i,j are indicating a matrix element of self.matrix_pm_id and self.matrix_day, each representing a dataset
        for a given list of pm_id_indices (an array of length count_days) create a list of dates

        returns a list of dates (an array of length count_days) for every given tuple (i,j)
        """

        count_pm_ids = self.matrix_pm_id[i][j]
        count_days = self.matrix_day[i][j]

        # how many days per pm_id:
        dict_count_days = {}
        for i in range(count_pm_ids):
            dict_count_days[i] = 0

        for index_ in person_id_indices:
            dict_count_days[index_] += 1

        min_date = datetime.date.fromisoformat(self.date_range[0])
        max_date = datetime.date.fromisoformat(self.date_range[1])
        # find a start date and a stop date for the number of days:
        max_min_date = max_date - min_date  # max_min_date validated to be positive in validate_config_file()

        dict_dates = {}
        for id in dict_count_days:  # this is a heuristic, expecting that after 100 additional days, enough unique days (see below remain)
            # if the heuristic fails, the assert below kicks in. Then a more deterministic solution should be implemented
            days_offset = int(self.random.integers(0, max_min_date.days-dict_count_days[id]))
            start_date = min_date + datetime.timedelta(days=days_offset)
            stop_date = start_date + datetime.timedelta(days=dict_count_days[id])
            assert stop_date > start_date
            dict_dates[id] = start_date, stop_date, stop_date - start_date

        dates = []
        for id in dict_count_days:
            for a in range(dict_dates[id][2].days):
                dates.append(dict_dates[id][0] + datetime.timedelta(a))

        #dates = sorted(set(dates))
        return dates

    def sim_PG_daily_stats(self, count_days) -> tuple:  
        # simulate plasma glucose (PG) statistical variables
        # simulate for all days (count_days), 
        # do not take into account information from actual data, correlations, etc.
        # Possible future improvement:have an individual mean and std per pm_id
        
        PG_mean = self.random.normal(120, 20, count_days)
        PG_std = self.random.normal(20, 15, count_days)
        PG_min, PG_max, PG_count = [], [], []
        min_factor = self.random.normal(3, 1, count_days)
        max_factor = self.random.normal(4, 1, count_days)
        for k in range(count_days):
            PG_min.append(PG_mean[k] - min_factor[k]*PG_std[k])
            PG_max.append(PG_mean[k] + max_factor[k]*PG_std[k])
            PG_count.append(288) # 288: 24h*measurements every 5 min

        return PG_mean, PG_std, PG_min, PG_max, PG_count


    def validate_config_file(self):
        # check that the dimension of the matrix is compatible with the number of datasets
        # that it is a square matrix (?)
        # that the dimensions of the matrix_pm_id and matrix_day are identical
        # that there are more days than project_member_ids
        matrix_pm_id = np.array(self.matrix_pm_id)
        
        matrix_day = np.array(self.matrix_day)
        assert self.count_datasets == matrix_day.shape[0]
        assert matrix_day.shape[0] == matrix_day.shape[1]  # square matrix       
        assert matrix_day.shape == matrix_pm_id.shape
        
        assert (matrix_day >= matrix_pm_id).all(), f"number of days needs to be bigger or equal to the number of project member ids: {(matrix_day > matrix_pm_id)}"

        assert self.date_range[1] > self.date_range[0], f"start and stop date for all datasets need to be meaningful in that stop date is after the start date ({self.date_range})"
        

        print(self.IO_json)

    def create_one_dataset(self, i : int, j : int):
        """
        return data per day for one dataset
        PG: plasma glucose

        first simulate project member ids, then dates for these pm_ids
        """
        count_pm_ids = self.matrix_pm_id[i][j]
        count_days = self.matrix_day[i][j]
        if count_days < 1: print(f"Warning: count_days was < 1 ({count_days}) for (i: {i},j: {j})")
        pm_ids1, pm_ids2, person_id_indices = self.sim_pm_ids(i, j)
        dates = self.sim_dates(i, j, person_id_indices)

        PG_mean, PG_std, PG_min, PG_max, PG_count = self.sim_PG_daily_stats(count_days)

        # date,sgv_mean,sgv_std,sgv_min,sgv_max,sgv_count,filename,user_id
        data = []
        for k in range(len(dates)):
            # do a second pm_id column, if not i==j
            if i==j:
                # mean, std, min, max, count, filename, pm_id
                data.append([dates[k], PG_mean[k], PG_std[k], PG_min[k], PG_max[k], PG_count[k], f"test_{i}_{j}.csv", pm_ids1[k]])  
            else:
                data.append([dates[k], PG_mean[k], PG_std[k], PG_min[k], PG_max[k], PG_count[k], f"test_{i}_{j}.csv", pm_ids1[k], pm_ids2[k]])
        return data

    def loop(self):
        """
        loop through all datasets
        simulate all datasets in the matrix (i, j). 
        Only the datasets for i>=j need to be simulated using create_one_dataset(i,j). 
        (2,1) is the same as (1,2), therefore it can be copied.
        """
        # create days for each combination of (i,j) 
        cols = ["date", "sgv_mean", "sgv_std", "sgv_min", "sgv_max", "sgv_count", "filename"]
        for i in range(self.count_datasets):
            self.days.append([])  # data as a list of rows
            self.df_days.append([])  # the corresponding dataframe
            for j in range(self.count_datasets):
                if j >= i: day_data = self.create_one_dataset(i,j)
                else: day_data = self.days[j][i]
                self.days[i].append(day_data)

                cols2 = deepcopy(cols)
                if i==j:
                    cols2.append(f"pm_id_{i}")
                else:
                    cols2.append(f"pm_id_{i}")
                    cols2.append(f"pm_id_{j}")
                df = pd.DataFrame(data=self.days[i][j], columns=cols2)
                cols2 = deepcopy(cols)
                cols2.append(f"pm_id_{i}")
                self.df_days[i].append(df[cols2])

        # mix them:
        self.df_days_compiled = []*self.count_datasets  # compiled across the different tuples self.df_days[i][j] all become aggregated into self.df_days[i]
        for i in range(self.count_datasets):
            self.df_days_compiled.append(pd.concat(self.df_days[i][:], axis=0))

        """
            self.df_days_compiled.append([])
            for j in range(self.count_datasets):
                if j == i:
                    self.df_days_compiled[i] = self.df_days[i][i]
                elif j > i:
                    cols2 = cols
                    cols2.append(f"pm_id_{j}")
        """                             


def main(config_filename : str = "config_master_sim.json", config_path : str = "config"):
    # print("you can run it on one duplicate plot-pair, or you run it on all of them as they are listed in config.json. See class all_duplicates.")
    ad = artificialDatasets(config_filename, config_path)
    ad.loop()

if __name__ == "__main__":
    fire.Fire(main)
