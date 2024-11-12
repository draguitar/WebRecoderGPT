//webkitURL is deprecated but nevertheless
URL = window.URL || window.webkitURL;

var gumStream; //stream from getUserMedia()
var displayStream; //stream from getDisplayMedia()
var recorder; //WebAudioRecorder object
var input; //MediaStreamAudioSourceNode for mic
var systemAudioInput; //MediaStreamAudioSourceNode for system audio
var encodingType; //holds selected encoding for resulting audio (file)
var encodeAfterRecord = true; // when to encode

// shim for AudioContext when it's not avb.
var AudioContext = window.AudioContext || window.webkitAudioContext;
var audioContext; //new audio context to help us record

var encodingTypeSelect = document.getElementById("encodingTypeSelect");
var recordButton = document.getElementById("recordButton");
var stopButton = document.getElementById("stopButton");
var summaryDiv = document.getElementById("summaryDiv");

var sessionId;

//add events to those 2 buttons
recordButton.addEventListener("click", startRecording);
stopButton.addEventListener("click", stopRecording);

async function startRecording() {
  console.log("startRecording() called");

  sessionId = document.getElementById("sessionId").value;

  alert(sessionId);

  recordButton.disabled = true;
  recordButton.classList.remove("active");
  recordButton.classList.add("disabled");

  stopButton.disabled = false;
  stopButton.classList.remove("disabled");
  stopButton.classList.add("active");

  try {
    // 創建音訊上下文
    audioContext = new AudioContext();

    // 獲取麥克風音訊
    const micStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false,
    });

    // 獲取系統音訊
    const systemStream = await navigator.mediaDevices.getDisplayMedia({
      audio: true,
      video: true,
    });

    // 儲存流以便後續停止使用
    gumStream = micStream;
    displayStream = systemStream;

    // 創建音訊源節點
    const micInput = audioContext.createMediaStreamSource(micStream);
    const systemInput = audioContext.createMediaStreamSource(systemStream);

    // 創建混音器節點
    const merger = audioContext.createChannelMerger(2);

    // 連接音訊節點
    micInput.connect(merger, 0, 0);
    systemInput.connect(merger, 0, 1);

    // 更新格式顯示
    document.getElementById("formats").innerHTML =
      "Format: 2 channel " +
      encodingTypeSelect.options[encodingTypeSelect.selectedIndex].value +
      " @ " +
      audioContext.sampleRate / 1000 +
      "kHz";

    // 禁用編碼選擇器
    encodingTypeSelect.disabled = true;

    // 獲取編碼類型
    encodingType =
      encodingTypeSelect.options[encodingTypeSelect.selectedIndex].value;

    // 初始化錄音機
    recorder = new WebAudioRecorder(merger, {
      workerDir: "static/js/",
      encoding: encodingType,
      numChannels: 2,
      onEncoderLoading: function (recorder, encoding) {
        __log("Loading " + encoding + " encoder...");
      },
      onEncoderLoaded: function (recorder, encoding) {
        __log(encoding + " encoder loaded");
      },
    });

    recorder.onComplete = function (recorder, blob) {
      __log("Encoding complete");
      createDownloadLink(blob, recorder.encoding);
      autoUpload(blob, recorder);

      encodingTypeSelect.disabled = false;
    };

    recorder.setOptions({
      timeLimit: 180,
      encodeAfterRecord: encodeAfterRecord,
      ogg: { quality: 0.9 },
      mp3: { bitRate: 192 },
    });

    recorder.startRecording();
    __log("Recording started");
  } catch (err) {
    console.error("Error starting recording:", err);
    __log("Error starting recording: " + err.message);
    if (err.name === "NotAllowedError") {
      alert("權限被拒絕。請允許訪問音訊設備。");
    } else if (err.name === "NotFoundError") {
      alert("找不到音訊設備。請檢查您的設備設置。");
    } else {
      alert("獲取音訊流時發生錯誤：" + err.message);
    }
    //重新載入
    reload_page();
  }
}

function stopRecording() {
  console.log("stopRecording() called");

  recordButton.disabled = false;
  recordButton.classList.remove("disabled");
  recordButton.classList.add("active");

  stopButton.disabled = true;
  stopButton.classList.remove("active");
  stopButton.classList.add("disabled");

  // 停止所有音訊軌道
  if (gumStream) {
    gumStream.getAudioTracks().forEach((track) => track.stop());
  }
  if (displayStream) {
    displayStream.getAudioTracks().forEach((track) => track.stop());
  }

  stopButton.disabled = true;
  recordButton.disabled = false;

  recorder.finishRecording();
  __log("Recording stopped");
  __log("資料彙整中請稍後...");
}

function createDownloadLink(blob, encoding) {
  var url = URL.createObjectURL(blob);
  var au = document.createElement("audio");
  var li = document.createElement("li");
  var link = document.createElement("a");

  //add controls to the <audio> element
  au.controls = true;
  au.src = url;

  //link the a element to the blob
  link.href = url;
  link.download = new Date().toISOString() + "." + encoding;
  link.innerHTML = link.download;

  //add the new audio and a elements to the li element
  li.appendChild(au);
  li.appendChild(link);

  //add the li element to the ordered list
  recordingsList.appendChild(li);
}

function autoUpload(blob) {
  // 建立 FormData 物件來傳送檔案
  const formData = new FormData();
  // Params
  // @blob
  // @filename
  // const uniqueId = crypto.randomUUID();
  const uniqueId = sessionId;
  formData.append("audio_file", blob, uniqueId + "." + recorder.encoding);
  // 使用 Fetch API 發送到 Flask 後端
  fetch("/autoUpload", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      const downloadTranscrLink = document.getElementById(
        "downloadTranscrLink"
      );
      downloadTranscrLink.href = "/download/" + uniqueId;
      // const pre = document.getElementById("log");
      // pre.textContent += "\n" + data.summary;
      summaryDiv.innerHTML += data.summary;
      console.log("Success:", data);
      __log("File uploaded successfully");
    })
    .catch((error) => {
      console.error("Error:", error);
      __log("Error uploading file");
    });
}

function reload_page() {
  document.getElementById("err_msg").value = "Permission denied";
  document.getElementById("form_err").submit();
}

//helper function
function __log(e, data) {
  log.innerHTML += e + " " + (data || "");
}
