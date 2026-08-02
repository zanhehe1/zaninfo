from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/zan')
def zan_info():
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"success": False, "error": "Missing uid"}), 400
    
    try:
        url = f"https://ff.garena.com/api/antihack/check_banned?lang=vi&uid={uid}"
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        
        if r.status_code == 200:
            data = r.json().get("data", {})
            return jsonify({
                "success": True,
                "uid": uid,
                "nickname": data.get("nickname", "N/A"),
                "level": data.get("level", "N/A"),
                "rank": data.get("rank", "N/A"),
                "region": data.get("region", "VN"),
                "is_banned": data.get("is_banned", 0)
            })
        return jsonify({"success": False, "error": "Cannot fetch"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

handler = app