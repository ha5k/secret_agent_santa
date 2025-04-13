
import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle

## Read In Form for Drawing Route Cards
family, forms, facilitator = sas_utils.load_pickles()