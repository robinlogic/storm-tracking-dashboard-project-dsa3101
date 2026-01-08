import numpy as np
import pandas as pd
from scipy.spatial import distance
from scipy.stats import chi2
from sklearn.preprocessing import StandardScaler

def mahalanobis(df):

    #Standardise storm area, distance and duration
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df[["storm_area_km2", "storm_distance_km", "storm_duration_min"]])
    df_scaled = pd.DataFrame(scaled_features, columns=["area_z", "distance_z", "duration_z"])

    # Compute Mahalanobis distance and return storm IDs of outliers as pd series
    data = df_scaled[['area_z', 'distance_z', 'duration_z']]
    cov_matrix = np.cov(data.values, rowvar=False)
    inv_cov = np.linalg.pinv(cov_matrix)
    mean_vec = data.mean().values
    
    diff = data.values - mean_vec
    left = np.dot(diff, inv_cov)
    mahal_sq = np.einsum('ij,ij->i', left, diff)
    distances = np.sqrt(mahal_sq)
    
    threshold = distances.mean() + 3 * distances.std()
    outliers = df.loc[distances > threshold, 'storm_id']
    
    return outliers

