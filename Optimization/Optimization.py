from shared_states import shelf_properties
import DB.DB_Back as db

## for ML
import pandas as pd
from datetime import timedelta
import numpy as np
from itertools import combinations
from google import genai
import json

from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# for LP
from pulp import LpProblem, LpVariable, LpMinimize, LpStatus, value


def Products_Projects_Merge():
	"""
	Merges product data with their associated projects.
	Returns:
		dict: A dictionary with product IDs as keys and merged data as values.
		list: A list of product IDs that do not have associated projects.
	"""
	products = db.Get_Products()
	projects = db.Get_Products_Projects()

	products_project = {}
	productIDs_without_project = []

	for pid, pdata in products.items():
		merged = pdata.copy()

		if pid in projects:
			merged["projects"] = projects[pid]
		else:
			productIDs_without_project.append(pid)
		products_project[pid] = merged

	return products_project, productIDs_without_project

def Transactions_Sessions_Creation(Products_without_Projects, products, time_window_minutes=5):
	"""
	Creates transaction sessions based on product inventory records.
	Args:
		Products_without_Projects (dict): A dictionary of products without their associated projects.
	Returns:
		list: A list of transaction sessions.
	"""
	Transactions = []
	for ProductID in Products_without_Projects:
		transact = db.Get_Product_Inventory_Records(ProductID) #Time, Quantity_Added, Quantity_Removed, Operator_ID, Project_Name, Shelf_ID
		
		for t in transact:
			row = {}
			row["Time"] = t["Time"]
			row["Product_ID"] = ProductID
			row["Name"] = products[ProductID]["Name"]
			row["Description"] = products[ProductID]["Description"]
			row["Quantity_Removed"] = t["Quantity_Removed"]
			row["Operator_ID"] = t["Operator_ID"]

			Transactions.append(row)
	Data = pd.DataFrame(Transactions)
	Data.sort_values(["Operator_ID", "Time"]).reset_index(drop=True)

	Data = Data.reset_index(drop=True)

	# === Define time window (5 minutes) ===
	time_window = timedelta(minutes=time_window_minutes)

	# === Create session IDs ===
	session_ids = []
	current_session = 0

	for i, row in Data.iterrows():
		if i == 0:
			session_ids.append(current_session)
			continue

		same_operator = Data.loc[i, "Operator_ID"] == Data.loc[i - 1, "Operator_ID"]
		time_diff = Data.loc[i, "Time"] - Data.loc[i - 1, "Time"]

		# If operator changes or time gap exceeds window → new session
		if (not same_operator) or (time_diff > time_window):
			current_session += 1
		session_ids.append(current_session)

	Data["Session_ID"] = session_ids

	# Filter out sessions that have only one unique product
	session_counts = Data.groupby("Session_ID")["Product_ID"].nunique()
	valid_sessions = session_counts[session_counts > 1].index
	Data = Data[Data["Session_ID"].isin(valid_sessions)]


	return Data

def CoOccurrence_Matrix_Creation(Transaction_Sessions):
	"""
	Creates a co-occurrence matrix from transaction sessions.
	Args:
		Transaction_Sessions (DataFrame): A DataFrame containing transaction sessions.
	Returns:
		DataFrame: A co-occurrence matrix of products.
		products (list): A list of unique product IDs.
		descriptions (dict): A dictionary mapping product IDs to their descriptions.
	"""
	Transaction_Sessions["Product_ID"] = Transaction_Sessions["Product_ID"].astype(str)

	product_sessions = Transaction_Sessions.groupby("Session_ID")["Product_ID"].apply(set).reset_index()
	products = sorted(Transaction_Sessions["Product_ID"].unique())
	descriptions = (
		Transaction_Sessions.drop_duplicates("Product_ID").set_index("Product_ID")["Description"].to_dict()
	)
	product_index = {p: i for i, p in enumerate(products)}

	# Initialize co-occurrence matrix
	co_matrix = np.zeros((len(products), len(products)), dtype=np.float32)

	# Fill co-occurrences
	for session_products in product_sessions["Product_ID"]:
		for a, b in combinations(session_products, 2):
			i, j = product_index[a], product_index[b]
			co_matrix[i, j] += 1
			co_matrix[j, i] += 1

	# Convert to DataFrame
	co_df = pd.DataFrame(co_matrix, index=products, columns=products)

	# Normalize co-occurrence matrix
	co_df = co_df.div(co_df.sum(axis=1), axis=0).fillna(0)
	return co_df, products, descriptions

def Clustering(co_df, products, descriptions):
	"""
	Performs K-means clustering on the co-occurrence matrix.
	Args:
		co_df (DataFrame): A co-occurrence matrix of products.
	Returns:
		DataFrame: A DataFrame containing product IDs, their assigned clusters, and descriptions.
	"""
	# Vary dimensionality and K cluster and find best silhouette score within ranges
	best_score = -np.inf
	best_n = None
	best_k = None

	k_min, k_max = 4, 10

	for n in range(5, 20):
		svd = TruncatedSVD(n_components=n, random_state=42)
		X_red = svd.fit_transform(co_df)

		for k in range(k_min, k_max + 1):
			km = KMeans(n_clusters=k, random_state=42, n_init=10)
			labels = km.fit_predict(X_red)
			sc = silhouette_score(X_red, labels)
			if sc > best_score:
				best_score = sc
				best_n = n
				best_k = k

	print(f"Best silhouette = {best_score:.6f} at n = {best_n}, k = {best_k}")

	svd = TruncatedSVD(n_components=best_n, random_state=42)
	X_red = svd.fit_transform(co_df)


	km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
	labels = km.fit_predict(X_red)
	cluster_df = pd.DataFrame({"Product_ID": products, "Cluster": labels})

	cluster_df["Description"] = cluster_df["Product_ID"].map(descriptions)
	return cluster_df


def Gemini_Verify_Clusters(cluster_df):
	"""
	Verifies clusters using the Gemini model.
	Args:
		cluster_df (DataFrame): A DataFrame containing product IDs and their assigned clusters.
	Returns:
		dict: A dictionary with cluster labels as keys and lists of product IDs as values.
	"""
	content = (prompt ) = f"""
	You are analyzing clustered product data.
	Here are the product names grouped by cluster:

	{cluster_df.groupby("Cluster")["Description"].apply(list).to_dict()}

	For each cluster, describe:
	1. What common purpose or use these products share.
	2. A short category name (2–3 words).
	3. Whether this cluster appears clean or should be split.
	Output in JSON as:
	[
	{{
		"cluster_id": 0,
		"summary": "...",
		"category": "...",
		"action": "keep/split"
	}},
	...
	]
	"""

	# Only run this block for Gemini Developer API
	client = genai.Client(api_key="YOUR_API_KEY_HERE")

	response = client.models.generate_content(
		model="gemini-2.5-pro",
		contents=content,
	)
	
	cluster_analysis = json.loads(response.text)
	cluster_actions = {}
	split_clusters = []
	for item in cluster_analysis:
		cluster_actions[item["cluster_id"]] = item # "cluster_id", "summary", "category", "action"
		if item["action"] == "split":
			print(f"Cluster {item['cluster_id']} marked for splitting.")
			split_clusters.append(item["cluster_id"])
		

	return cluster_actions, split_clusters

def Categorize_Products():
	"""
	Categorizes products using K-means clustering based on co-occurrence in transactions.
	Args:
		Products_without_Projects (dict): A dictionary of products without their associated projects.
	Returns:
		dict: A nested dictionary categorizing products by family and project.
	"""
	products_project, productIDs_without_project = Products_Projects_Merge()
	Transaction_Sessions = Transactions_Sessions_Creation(productIDs_without_project, products_project)
	co_df, products, descriptions = CoOccurrence_Matrix_Creation(Transaction_Sessions)
	cluster_df = Clustering(co_df, products, descriptions)
	cluster_results, split_clusters = Gemini_Verify_Clusters(cluster_df)

	# Prepare final categorized structure
	
	for product_id in productIDs_without_project:
		cluster_id = cluster_df.loc[cluster_df["Product_ID"] == product_id, "Cluster"].values[0]
		project = cluster_results[cluster_id]["category"]

		products_project[product_id]["projects"] = project
	

	return products_project