import pandas as pd

def read_form(url_in):
    url_use = url_in.replace('/edit#gid=', '/export?format=csv&gid=')
    return pd.read_csv(url_use)
