import os
import re
import time
import traceback
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
import joblib
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
BUNDLE_PATH = APP_DIR / "internship_company_recommender.joblib"
CSV_INPUT = APP_DIR / "internshipdata.csv"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
_bundle = None

def load_bundle():
    global _bundle
    if _bundle is not None:
        return _bundle
    if BUNDLE_PATH.exists():
        try:
            _bundle = joblib.load(BUNDLE_PATH)
            app.logger.info("Loaded joblib bundle from %s", BUNDLE_PATH)
            return _bundle
        except Exception as e:
            app.logger.error("Failed to load joblib bundle: %s", e)
            # continue to fallback training
    # Fallback: try to train quickly from CSV if present, else train tiny synthetic model
    try:
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder
    except Exception:
        raise RuntimeError("scikit-learn must be installed in the environment")

    if CSV_INPUT.exists():
        df = pd.read_csv(CSV_INPUT)
    else:
        # small synthetic dataset so frontend works even without joblib file
        def synthetic():
            rows = [
                ["Riya Sharma",21,"Female","Delhi",8.6,"python ml data","3","Google","Bangalore","python ml sql","YES",4],
                ["Aarav Mehta",22,"Male","Mumbai",7.9,"java spring sql","6","Infosys","Pune","java spring","YES",3],
                ["Neha Patel",20,"Female","Pune",8.2,"html css js react","2","TCS","Mumbai","react js","YES",3],
                ["Aditya Singh",21,"Male","Bangalore",7.5,"python django","4","Wipro","Hyderabad","python django","YES",2],
                ["Priya Verma",23,"Female","Chennai",9.1,"ml deep-learning python","6","Google","Bangalore","ml deep-learning","YES",4],
                ["Rajesh Gupta",22,"Male","Hyderabad",7.2,"c++ dsa","0","Infosys","Pune","dsa c++","NO",0],
                ["Simran Kaur",20,"Female","Delhi",8.9,"react node mongodb","3","Microsoft","Hyderabad","react node","YES",4],
                ["Mohit Rao",21,"Male","Pune",7.8,"sql excel powerbi","2","Deloitte","Mumbai","sql excel","YES",3],
                ["Anjali Desai",22,"Female","Mumbai",8.5,"flutter firebase","4","Swiggy","Bangalore","flutter firebase","YES",4],
                ["Karan Yadav",21,"Male","Bangalore",7.4,"java dsa","0","Infosys","Pune","java dsa","NO",0],
            ]
            cols = ["Student name","Age","Gender","Location","CGPA","Technical skills","Work experience",
                    "Company name","Company location","Skills required by company","Internship status","Rating by company"]
            return pd.DataFrame(rows, columns=cols)
        df = synthetic()

    # minimal preprocessing
    df['Age'] = pd.to_numeric(df['Age'], errors='coerce').fillna(df['Age'].median())
    df['CGPA'] = pd.to_numeric(df['CGPA'], errors='coerce').fillna(df['CGPA'].median())
    df['Rating by company'] = pd.to_numeric(df['Rating by company'], errors='coerce').fillna(0)
    df['Work experience months'] = df['Work experience'].astype(str).str.extract(r'(\d+)').fillna(0).astype(int)
    df['Internship status bin'] = df['Internship status'].astype(str).map({'YES':1,'NO':0}).fillna(0).astype(int)

    le_gender = LabelEncoder().fit(df['Gender'].astype(str)); df['Gender_enc'] = le_gender.transform(df['Gender'].astype(str))
    le_location = LabelEncoder().fit(df['Location'].astype(str)); df['Location_enc'] = le_location.transform(df['Location'].astype(str))
    le_company_loc = LabelEncoder().fit(df['Company location'].astype(str)); df['Company_location_enc'] = le_company_loc.transform(df['Company location'].astype(str))
    le_company = LabelEncoder().fit(df['Company name'].astype(str)); df['Company_enc'] = le_company.transform(df['Company name'].astype(str))

    vectorizer = CountVectorizer(token_pattern=r'(?u)\b\w+\b')
    skill_matrix = vectorizer.fit_transform(df['Technical skills'].astype(str))

    X_num = df[['Age','Gender_enc','CGPA','Location_enc','Company_location_enc','Work experience months','Internship status bin','Rating by company']].reset_index(drop=True)
    X_skills = pd.DataFrame(skill_matrix.toarray(), columns=[f"skill_{s}" for s in vectorizer.get_feature_names_out()])
    X = pd.concat([X_num, X_skills], axis=1)
    X.columns = X.columns.astype(str)
    y = df['Company_enc']

    # train small random forest
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X, y)

    _bundle = {
        "model": model,
        "vectorizer": vectorizer,
        "le_gender": le_gender,
        "le_location": le_location,
        "le_company_loc": le_company_loc,
        "le_company": le_company,
        "feature_columns": X.columns.tolist()
    }
    # try to persist so next start uses it
    try:
        joblib.dump(_bundle, str(BUNDLE_PATH))
        app.logger.info("Saved fallback bundle to %s", BUNDLE_PATH)
    except Exception:
        app.logger.warning("Could not save fallback bundle (permissions?)")
    _bundle = _bundle
    return _bundle

def safe_label_encode(le, value):
    try:
        if value in list(le.classes_):
            return int(le.transform([value])[0])
    except Exception:
        pass
    return 0

@app.route("/")
def index():
    return send_static("index.html")

@app.route("/results")
def results_page():
    return send_static("results.html")

@app.route("/insights")
def insights_page():
    return send_static("insights.html")

@app.route("/history")
def history_page():
    return send_static("history.html")

@app.route("/feedback.html")
def feedback_page():
    return send_static("feedback.html")

def send_static(name):
    return send_from_directory(str(STATIC_DIR), name)

@app.route("/api/predict", methods=["POST"])
def api_predict():
    try:
        bundle = load_bundle()
    except Exception as e:
        return jsonify({"ok": False, "error": f"Model load/train error: {e}"}), 500

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "error": "Invalid or empty JSON body"}), 400

    try:
        # build student dict
        student = {
            "Age": int(data.get("Age", 21)),
            "Gender": data.get("Gender", "Male"),
            "Location": data.get("Location", "Delhi"),
            "CGPA": float(data.get("CGPA", 8.0)),
            "Technical skills": data.get("Technical skills", ""),
            "Work experience": data.get("Work experience", "0"),
            "Company location": data.get("Company location", "Bangalore"),
            "Rating by company": int(data.get("Rating by company", 0)),
            "Internship status": data.get("Internship status", "NO")
        }

        # vectorize skills
        vec = bundle["vectorizer"].transform([student["Technical skills"]])
        skill_cols = [f"skill_{s}" for s in bundle["vectorizer"].get_feature_names_out()]
        skills_df = pd.DataFrame(vec.toarray(), columns=skill_cols)

        row = {
            "Age": student["Age"],
            "Gender_enc": safe_label_encode(bundle["le_gender"], student["Gender"]),
            "CGPA": student["CGPA"],
            "Location_enc": safe_label_encode(bundle["le_location"], student["Location"]),
            "Company_location_enc": safe_label_encode(bundle["le_company_loc"], student["Company location"]),
            "Work experience months": int(re.search(r"(\\d+)", str(student["Work experience"]) or "0").group(1)) if re.search(r"(\\d+)", str(student["Work experience"])) else 0,
            "Internship status bin": 1 if str(student["Internship status"]).upper() == "YES" else 0,
            "Rating by company": student["Rating by company"]
        }

        X_new = pd.DataFrame([row])
        X_new = pd.concat([X_new.reset_index(drop=True), skills_df], axis=1)

        # add missing features
        for c in bundle["feature_columns"]:
            if c not in X_new.columns:
                X_new[c] = 0
        X_new = X_new[bundle["feature_columns"]]

        model = bundle["model"]
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_new)[0]
            # build class labels for the probabilities
            classes = bundle["le_company"].inverse_transform(list(range(len(probs))))
            pairs = sorted(list(zip(classes, probs)), key=lambda x: x[1], reverse=True)[:5]
            top3 = pairs[:3]
        else:
            pred_enc = model.predict(X_new)[0]
            comp = bundle["le_company"].inverse_transform([pred_enc])[0]
            top3 = [(comp, 1.0)]

        # matched skills heuristic if CSV exists
        matched = {}
        try:
            if CSV_INPUT.exists():
                df = pd.read_csv(CSV_INPUT)
                for c,_ in top3:
                    reqs = df[df["Company name"]==c]["Skills required by company"].astype(str).tolist()
                    tokens = []
                    for r in reqs:
                        tokens += re.findall(r"\w+", r.lower())
                    student_tokens = re.findall(r"\w+", student["Technical skills"].lower())
                    matched[c] = list(set(tokens) & set(student_tokens))
            else:
                for c,_ in top3:
                    matched[c] = []
        except Exception:
            for c,_ in top3:
                matched[c] = []

        response = {
            "ok": True,
            "top3": [(c, float(p)) for c,p in top3],
            "matched": matched,
            "notes": "Top-3 companies (model probabilities).",
            "ts": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return jsonify(response)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run()

