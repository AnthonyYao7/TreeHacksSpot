# terra-python
import logging
import flask
from flask import request
from terra.base_client import Terra

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger("app")

terra = Terra(api_key='tmrHjwLQuYDgKXwXRcltrBN_cCEcTyhs', dev_id='terraapitest-testing-UbidJIemMU', secret="912dea01818b97b313312af52ed65f6372224d76eaec5889")

app = flask.Flask(__name__)

@app.route("/consumeTerraWebhook", methods=["POST"])
def consume_terra_webhook() -> flask.Response:
    # body_str = str(request.get_data(), 'utf-8')
    body = request.get_json()
    _LOGGER.info(
        "Received webhook for user %s of type %s",
        body.get("user", {}).get("user_id"),
        body["type"])
    verified = terra.check_terra_signature(request.get_data().decode("utf-8"), request.headers['terra-signature'])
    data_inner_dict = body["data"][0]
    potentials_ecg_list = data_inner_dict["heart_data"]["ecg_signal"][0]["raw_signal"] #Emulating the fetching of data from wearable device using Terra API
    #Exponentially weighted moving averages
    disorder = False
    THRESH_VAL = 100
    TOTAL_LEN = len(potentials_ecg_list)
    BATCH_SIZE = 5
    alpha = 2.0 / (BATCH_SIZE + 1)
    curAvg = 0.0
    iterVal = 0
    for initVal in potentials_ecg_list[:BATCH_SIZE]:
       curAvg += abs(initVal["potential_uV"])
    curAvg /= BATCH_SIZE
    for elem in potentials_ecg_list[BATCH_SIZE:]:
      curAvg = (alpha * abs(curAvg)) + ((1 - alpha) * abs(elem["potential_uV"]))
      # Debugging/Testing
      # print(elem["potential_uV"])
      if (curAvg > THRESH_VAL):
         iterVal += 1
      if (iterVal > int(0.1 * TOTAL_LEN)):
         print("Warning! Heart patterns indicate risk of heart arrhythmia!")
         disorder = True
         break
    if (not disorder):
       print("Heart rate appears to be healthy!")
    if verified:
      return flask.Response(status=200)
    else:
      return flask.Response(status=403)
    
    
if __name__ == "__main__":
    app.run(host="localhost", port=8000)