from flask import Blueprint, jsonify, request
from storm_database import StormDatabase

api = Blueprint("api", __name__)

db = StormDatabase()

@api.route("/api/frontend/get_raw_storm_data", methods=["GET"])
def get_raw_storm_data():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    res = db.get_storm_profiles(start_date, end_date)
    
    
    return jsonify({
        "storm_profiles_raw": res.to_dict(orient="records")
    })

@api.route("/api/frontend/get_clean_storm_data", methods=["GET"])
def get_clean_storm_data():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    res = db.get_storm_profiles(start_date, end_date)
    res_filtered = res[res["outlier"]==False].drop(columns = ["outlier"])
    
    return jsonify({
        "storm_profiles_clean": res_filtered.to_dict(orient="records")
    })

@api.route("/api/frontend/get_rainy_days_data", methods=["GET"])
def get_rainy_days_data():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    res = db.get_rainy_days(start_date, end_date)
    
    return jsonify({
        "rainy_days": res.to_dict(orient="records")
    })

@api.route("/api/frontend/get_other_storm_data", methods=["GET"])
def get_other_storm_data():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    res = db.get_other_storm_features(start_date, end_date)
    
    return jsonify({
        "other_storm_data": res.to_dict(orient="records")
    })