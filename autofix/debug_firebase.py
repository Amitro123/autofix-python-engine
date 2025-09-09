# debug_firebase.py
from firestore_client import get_metrics_collector

try:
    collector = get_metrics_collector()
    print(f"✅ Collector initialized: {collector}")
    print(f"✅ Project ID: {collector.project_id}")
    print(f"✅ App ID: {collector.app_id}")
    print(f"✅ Client active: {collector.client is not None}")
    
    # טסט ישיר
    result = collector.save_metrics(
        script_path="debug_test.py",
        status="manual_test",
        message="Manual Firebase test"
    )
    print(f"✅ Manual save result: {result}")
    
except Exception as e:
    print(f"❌ Firebase error: {e}")
    import traceback
    traceback.print_exc()
