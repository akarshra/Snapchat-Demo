
const getEl = (id) => document.getElementById(id);

const setDisplay = (element, visible, displayValue = "block") => {
  if (element) {
    element.style.display = visible ? displayValue : "none";
  }
};

function escapeHtml(text = "") {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const snapFile = getEl("snap-file");
const fileBtn = getEl("file-button");
const uploadPhotoBtn = getEl("upload-photo-button");
const previewDock = getEl("preview-dock");
const previewContainer = getEl("preview-container");
const caption = getEl("caption");
const closePreviewBtn = getEl("close-preview");

if (fileBtn) {
  fileBtn.addEventListener("click", () => {
    if (window.location.pathname.includes("/chat-details/")) {
      window.openCameraModal();
    } else if (snapFile) {
      snapFile.click();
    }
  });
}

if (uploadPhotoBtn && snapFile) {
  uploadPhotoBtn.addEventListener("click", () => {
    snapFile.click();
  });
}

if (snapFile && previewContainer && caption && previewDock) {
  snapFile.addEventListener("change", () => {
    const currentFile = snapFile.files[0];
    if (!currentFile) return;

    const previewUrl = URL.createObjectURL(currentFile);
    previewContainer.innerHTML = `
      <img
        id="preview-snap"
        src="${previewUrl}"
        alt="${escapeHtml(currentFile.name)}"
        class="object-cover h-full w-full"
      />
    `;

    caption.textContent = currentFile.name;
    setDisplay(previewDock, true, "block");
  });
}

if (closePreviewBtn && snapFile && previewDock) {
  closePreviewBtn.addEventListener("click", () => {
    snapFile.value = "";
    setDisplay(previewDock, false);
  });
}

if (window.location.search.includes("open=camera") && fileBtn) {
  const url = new URL(window.location);
  url.searchParams.delete("open");
  window.history.replaceState({}, document.title, url.pathname);
  fileBtn.click();
}

let callStream = null;

window.startCall = function (type) {
  const modal = getEl("calling-modal");
  const status = getEl("call-status");
  const videoContainer = getEl("video-container");
  const videoElement = getEl("call-video-preview");

  if (!modal) return;

  modal.classList.remove("hidden");
  if (status) status.textContent = "Calling...";

  if (type === "video") {
    setDisplay(videoContainer, true, "block");

    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((stream) => {
        callStream = stream;
        if (videoElement) videoElement.srcObject = stream;
        if (status) status.textContent = "Connected";
      })
      .catch((error) => {
        console.warn("Could not access camera/mic for call, simulating instead:", error);
        if (status) status.textContent = "Connected";
        setDisplay(videoContainer, false);
      });
  } else {
    setDisplay(videoContainer, false);

    setTimeout(() => {
      if (status) status.textContent = "Ringing...";
      setTimeout(() => {
        if (status) status.textContent = "Connected";
      }, 1500);
    }, 800);
  }
};

window.endCall = function () {
  const modal = getEl("calling-modal");
  if (modal) {
    modal.classList.add("hidden");
  }

  if (callStream) {
    callStream.getTracks().forEach((track) => track.stop());
    callStream = null;
  }
};

let activeCameraStream = null;
let capturedBlob = null;

function stopActiveCamera() {
  if (activeCameraStream) {
    activeCameraStream.getTracks().forEach((track) => track.stop());
    activeCameraStream = null;
  }
}

function updateSendToChatButton() {
  const sendToChatBtn = getEl("send-to-chat-btn");
  const context = getEl("camera-context");

  if (!sendToChatBtn) return;

  if (context && context.dataset.chatUserId) {
    sendToChatBtn.style.display = "flex";
    sendToChatBtn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Send to ${escapeHtml(context.dataset.chatUsername || "")}`;
  } else {
    sendToChatBtn.style.display = "none";
  }
}

window.openCameraModal = function () {
  const modal = getEl("camera-modal");
  const video = getEl("camera-stream");
  const fallback = getEl("camera-fallback");
  const preview = getEl("capture-preview-container");
  const shutter = getEl("shutter-button-container");
  const header = getEl("camera-header");

  if (!modal) return;

  modal.classList.remove("hidden");
  if (preview) preview.classList.add("hidden");
  if (fallback) fallback.classList.add("hidden");
  setDisplay(shutter, true, "flex");
  setDisplay(header, true, "flex");

  if (video) {
    video.classList.remove("hidden");
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "user" }, audio: false })
      .then((stream) => {
        activeCameraStream = stream;
        video.srcObject = stream;
      })
      .catch((error) => {
        console.warn("Camera access denied or unavailable, using fallback:", error);
        video.classList.add("hidden");
        if (fallback) fallback.classList.remove("hidden");
      });
  }

  updateSendToChatButton();
  fetchFriendsForCamera();
};

window.openCameraForFriend = function (friendId, friendUsername) {
  let context = getEl("camera-context");
  if (!context) {
    context = document.createElement("div");
    context.id = "camera-context";
    context.className = "hidden";
    document.body.appendChild(context);
  }

  context.dataset.chatUserId = friendId;
  context.dataset.chatUsername = friendUsername;
  window.openCameraModal();
};

window.openGeneralCamera = function () {
  const context = getEl("camera-context");
  if (context) {
    context.removeAttribute("data-chat-user-id");
    context.removeAttribute("data-chat-username");
  }
  window.openCameraModal();
};

window.closeCameraModal = function () {
  const modal = getEl("camera-modal");
  if (modal) modal.classList.add("hidden");
  stopActiveCamera();
};

window.triggerMockCaptureUpload = function () {
  const mockUploadInput = getEl("camera-mock-upload");
  if (mockUploadInput) mockUploadInput.click();
};

const cameraMockUpload = getEl("camera-mock-upload");
if (cameraMockUpload) {
  cameraMockUpload.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;

    capturedBlob = file;
    showCapturedPreview(URL.createObjectURL(file));
  });
}

window.capturePhoto = function () {
  const video = getEl("camera-stream");
  if (activeCameraStream && video) {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const context = canvas.getContext("2d");

    context.translate(canvas.width, 0);
    context.scale(-1, 1);
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      capturedBlob = new File([blob], "snap.jpg", { type: "image/jpeg" });
      showCapturedPreview(URL.createObjectURL(blob));
    }, "image/jpeg");
  } else {
    window.triggerMockCaptureUpload();
  }
};

function showCapturedPreview(url) {
  const preview = getEl("capture-preview-container");
  const img = getEl("captured-image-view");
  const shutter = getEl("shutter-button-container");
  const header = getEl("camera-header");

  if (shutter) shutter.style.display = "none";
  if (header) header.style.display = "none";

  if (preview && img) {
    img.src = url;
    preview.classList.remove("hidden");
    stopActiveCamera();
  }
}

window.retakePhoto = function () {
  const preview = getEl("capture-preview-container");
  if (preview) preview.classList.add("hidden");

  const shutter = getEl("shutter-button-container");
  const header = getEl("camera-header");
  setDisplay(shutter, true, "flex");
  setDisplay(header, true, "flex");

  window.openCameraModal();
};

function fetchFriendsForCamera() {
  fetch("/api/friends/")
    .then((response) => response.json())
    .then((data) => {
      const list = getEl("camera-friends-list");
      if (!list) return;

      list.innerHTML = "";

      if (!data.friends || data.friends.length === 0) {
        list.innerHTML = `<li class="p-4 text-xs text-gray-500 text-center">No friends yet. Add friends on Search!</li>`;
        return;
      }

      data.friends.forEach((friend) => {
        const li = document.createElement("li");
        li.innerHTML = `
          <a onclick="sendSnapToFriend(${friend.id}, '${friend.username}')" class="flex items-center gap-3 py-2 px-3 hover:bg-gray-100 cursor-pointer rounded-lg">
            <div class="avatar size-8 rounded-full overflow-hidden border border-gray-200">
              <img src="${friend.avatar_url}" class="w-full h-full object-cover" />
            </div>
            <span class="font-bold text-xs text-gray-800">${friend.username}</span>
          </a>
        `;
        list.appendChild(li);
      });
    })
    .catch((error) => console.error("Error loading friends list:", error));
}

window.sendSnapToFriend = function (friendId, username, target = "chat") {
  if (!capturedBlob) return;

  const formData = new FormData();
  formData.append("image", capturedBlob);
  formData.append("target", target);

  let csrf = "";
  const csrfInput = document.querySelector("[name=csrfmiddlewaretoken]");
  if (csrfInput) {
    csrf = csrfInput.value;
  } else {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) csrf = match[1];
  }

  fetch(`/send-message/${friendId}`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrf,
      "X-Requested-With": "XMLHttpRequest"
    },
    body: formData
  })
    .then(() => {
      window.closeCameraModal();
      capturedBlob = null;

      const preview = getEl("capture-preview-container");
      const img = getEl("captured-image-view");
      if (preview) preview.classList.add("hidden");
      if (img) img.src = "";
    })
    .catch((error) => {
      console.error("Error sending snap:", error);
      alert("Failed to send snap.");
    });
};

window.sendCapturedSnapToTarget = function (target) {
  const context = getEl("camera-context");
  if (!capturedBlob) return;

  if (!context || !context.dataset.chatUserId) {
    alert("Open this from a chat page to send to the current user.");
    return;
  }

  const friendId = context.dataset.chatUserId;
  const friendName = context.dataset.chatUsername || "this chat";
  const targetValue = target === "all_friends" ? "all_friends" : "chat";

  window.sendSnapToFriend(friendId, friendName, targetValue);
};

window.postToMyStory = function () {
  if (!capturedBlob) return;

  const reader = new FileReader();
  reader.onloadend = function () {
    const base64data = reader.result;
    const stories = JSON.parse(localStorage.getItem("my_stories") || "[]");

    stories.push({
      image: base64data,
      timestamp: new Date().getTime(),
      username: "Me"
    });

    localStorage.setItem("my_stories", JSON.stringify(stories));
    window.closeCameraModal();
    alert("Snap posted to My Story!");
  };

  reader.readAsDataURL(capturedBlob);
};

let storyIndex = 0;
let storyPlayInterval = null;
let currentStoriesList = [];
const STORY_DURATION = 4000;

window.openStoriesModal = function () {
  const modal = getEl("stories-modal");
  if (!modal) return;

  const myStories = JSON.parse(localStorage.getItem("my_stories") || "[]");
  const friendsStories = [
    {
      username: "Sarah Watson",
      avatar_url: "https://img.daisyui.com/images/profile/demo/yellingwoman@192.webp",
      image: "https://images.pexels.com/photos/1036622/pexels-photo-1036622.jpeg?auto=compress&cs=tinysrgb&w=800",
      time: "2h ago"
    },
    {
      username: "AnimeFan",
      avatar_url: "https://i.pinimg.com/736x/4a/32/dc/4a32dc90de96d69cea42a1d6280e3598.jpg",
      image: "https://images.pexels.com/photos/1375902/pexels-photo-1375902.jpeg?auto=compress&cs=tinysrgb&w=800",
      time: "4h ago"
    }
  ];

  const formattedMyStories = myStories.map((story) => ({
    username: "Me",
    avatar_url: "/static/snaps/default.jpg",
    image: story.image,
    time: "Just now"
  }));

  currentStoriesList = [...formattedMyStories, ...friendsStories];

  modal.classList.remove("hidden");
  storyIndex = 0;
  playStory();
};

window.closeStoriesModal = function () {
  const modal = getEl("stories-modal");
  if (modal) modal.classList.add("hidden");
  clearTimeout(storyPlayInterval);
};

function playStory() {
  clearTimeout(storyPlayInterval);
  
  if (storyIndex >= currentStoriesList.length) {
    closeStoriesModal();
    return;
  }
  
  const story = currentStoriesList[storyIndex];
  const avatar = getEl("story-user-avatar");
  const name = getEl("story-username");
  const time = getEl("story-time");
  const contentImg = getEl("story-image-content");
  const progressContainer = getEl("story-progress-bar");
  
  if (avatar) avatar.src = story.avatar_url || "/static/snaps/default.jpg";
  if (name) name.innerText = story.username;
  if (time) time.innerText = story.time;
  if (contentImg) contentImg.src = story.image;
  
  if (progressContainer) {
    progressContainer.innerHTML = "";
    for (let i = 0; i < currentStoriesList.length; i++) {
      const segment = document.createElement("div");
      segment.className = "h-1 bg-white/30 rounded-full grow overflow-hidden relative";
      
      const fill = document.createElement("div");
      fill.className = "absolute left-0 top-0 bottom-0 bg-white transition-all ease-linear";
      
      if (i < storyIndex) {
        fill.style.width = "100%";
      } else if (i === storyIndex) {
        fill.style.width = "0%";
        setTimeout(() => {
          fill.style.transitionDuration = `${STORY_DURATION}ms`;
          fill.style.width = "100%";
        }, 50);
      } else {
        fill.style.width = "0%";
      }
      
      segment.appendChild(fill);
      progressContainer.appendChild(segment);
    }
  }
  
  storyPlayInterval = setTimeout(() => {
    storyIndex++;
    playStory();
  }, STORY_DURATION);
}

document.addEventListener("DOMContentLoaded", () => {
  const chatContext = document.getElementById("chat-context");
  if (chatContext) {

  const friendId = chatContext.dataset.friendId;
  const currentUserId = parseInt(chatContext.dataset.currentUserId);
 
  const mainScroll = document.getElementById("chat-scroll-container");
  if (mainScroll) {
    mainScroll.scrollTop = mainScroll.scrollHeight;
  }

  let chatSocket = null;
  let chatPollInterval = null;

  function startChatPolling() {
    if (chatPollInterval) return;
    console.log("Fallback: Starting chat messages polling...");
    pollChatMessages();
    chatPollInterval = setInterval(pollChatMessages, 3000);
  }

  function pollChatMessages() {
    fetch(`/api/chat-messages/${friendId}/`)
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        updateChatMessages(data.messages);
      }
    })
    .catch(err => console.error("Error polling chat messages:", err));
  }

  function updateChatMessages(messages) {
    const container = document.getElementById("chat-messages-container");
    if (!container) return;

    const currentMsgIds = new Set();
    const msgElements = container.querySelectorAll("[data-message-id]");
    msgElements.forEach(el => {
      currentMsgIds.add(parseInt(el.dataset.messageId));
    });

    let newMsgAdded = false;
    messages.forEach(msg => {
      if (!currentMsgIds.has(msg.id)) {
        appendMessage(msg, currentUserId);
        newMsgAdded = true;
      }
    });

    if (newMsgAdded) {
      const mainScroll = document.getElementById("chat-scroll-container");
      if (mainScroll) {
        mainScroll.scrollTop = mainScroll.scrollHeight;
      }
    }
  }

  try {
    const wsProto = window.location.protocol === "https:" ? "wss://" : "ws://";
    chatSocket = new WebSocket(
      wsProto + window.location.host + "/ws/chat/" + friendId + "/"
    );

    chatSocket.onmessage = function(e) {
      const data = JSON.parse(e.data);
      const message = data.message;
      if (message.is_screenshot_alert) {
        showScreenshotToast(message.text);
      } else {
        appendMessage(message, currentUserId);
      }
    };

    chatSocket.onclose = function(e) {
      console.error("Chat socket closed unexpectedly.");
      startChatPolling();
    };
  } catch (err) {
    console.error("Failed to initialize WebSocket:", err);
    startChatPolling();
  }

  const deleteRadios = document.querySelectorAll("input[name='delete_option']");
  deleteRadios.forEach(radio => {
    radio.addEventListener("change", function() {
      const selectedOption = this.value;
      
      let csrf = "";
      const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
      if (csrfInput) {
        csrf = csrfInput.value;
      } else {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) csrf = match[1];
      }

      fetch(`/chat-details/${friendId}/update-delete-option/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({ "delete_option": selectedOption })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === "success") {
          console.log("Delete option updated successfully.");
          window.location.reload();
        } else {
          console.error("Failed to update delete option:", data.message);
        }
      })
      .catch(err => console.error("Error updating delete option:", err));
    });
  });

  const showStreakCheckbox = document.querySelector("input[name='show_streak']");
  if (showStreakCheckbox) {
    showStreakCheckbox.addEventListener("change", function() {
      const showStreak = this.checked;
      
      let csrf = "";
      const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
      if (csrfInput) {
        csrf = csrfInput.value;
      } else {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) csrf = match[1];
      }

      fetch(`/chat-details/${friendId}/update-streak-option/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({ "show_streak": showStreak })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === "success") {
          console.log("Streak option updated successfully.");
          window.location.reload();
        } else {
          console.error("Failed to update streak option:", data.message);
        }
      })
      .catch(err => console.error("Error updating streak option:", err));
    });
  }

  const chatForm = document.getElementById("chat-form");
  if (chatForm) {
    chatForm.addEventListener("submit", function(e) {
      e.preventDefault();

      const messageInput = chatForm.querySelector("input[name='message']");
      const messageText = messageInput.value.trim();
      const targetVal = e.submitter ? e.submitter.value : "chat";
      const snapFile = document.getElementById("snap-file");

      if (snapFile && snapFile.files.length > 0) {
       
        const formData = new FormData(chatForm);
        formData.append("target", targetVal);

        let csrf = "";
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) {
          csrf = csrfInput.value;
        } else {
          const match = document.cookie.match(/csrftoken=([^;]+)/);
          if (match) csrf = match[1];
        }

        fetch(chatForm.action, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrf,
            "X-Requested-With": "XMLHttpRequest"
          },
          body: formData
        })
        .then(res => {
          if (res.ok) {
            
            snapFile.value = "";
            messageInput.value = "";
            const previewDock = document.getElementById("preview-dock");
            if (previewDock) setDisplay(previewDock, false);
          } else {
            console.error("Failed to send image snap");
          }
        })
        .catch(err => console.error("Error sending image snap:", err));

      } else if (messageText) {
        
        chatSocket.send(JSON.stringify({
          "message": messageText,
          "target": targetVal
        }));
        messageInput.value = "";
      }
    });
  }

  let screenshotCooldown = false;
  const detectScreenshot = () => {
    if (screenshotCooldown) return;
    screenshotCooldown = true;
    setTimeout(() => { screenshotCooldown = false; }, 2000);

    let csrf = "";
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput) {
      csrf = csrfInput.value;
    } else {
      const match = document.cookie.match(/csrftoken=([^;]+)/);
      if (match) csrf = match[1];
    }

    fetch(`/chat-details/${friendId}/screenshot/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest"
      }
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        console.log("Screenshot notification sent.");
      }
    })
    .catch(err => console.error("Error triggering screenshot notification:", err));
  };

  window.addEventListener("keydown", (e) => {
    const isPrintScreen = e.key === "PrintScreen";
    const isMacScreenshot = e.metaKey && e.shiftKey;
    
    if (isPrintScreen || isMacScreenshot) {

      detectScreenshot();
    }
  });
  }

  const notificationsContext = document.getElementById("notifications-context");
  let notificationPollInterval = null;

  function startNotificationPolling() {
    if (notificationPollInterval) return;
    console.log("Fallback: Starting notification polling...");
    pollNotifications();
    notificationPollInterval = setInterval(pollNotifications, 3000);
  }

  function pollNotifications() {
    fetch("/api/unread-chats/")
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        updateNotificationRows(data.chats);
      }
    })
    .catch(err => console.error("Error polling notifications:", err));
  }

  function updateNotificationRows(chats) {
    chats.forEach(chat => {
      const row = document.getElementById("friend-row-" + chat.friend_id);
      if (row) {
        if (chat.has_unviewed) {
          const icon = row.querySelector("p i");
          if (icon) {
            icon.className = `fa-solid ${chat.last_message_type === "image" ? "fa-square text-red-500" : "fa-comment text-red-500"} fa-xs flex-shrink-0`;
          }
          const statusSpan = row.querySelector("p span:nth-of-type(1)");
          if (statusSpan) {
            statusSpan.innerText = chat.last_message_type === "image" ? "New Snap" : "New Message";
            statusSpan.className = "text-red-500 font-bold truncate";
          }
          const timeSpan = row.querySelector("p span:nth-of-type(2)");
          if (timeSpan) {
            timeSpan.innerText = chat.last_message_time;
          }

          const separatorSpan = row.querySelector("p span.size-1");
          if (separatorSpan) {
            separatorSpan.style.display = "";
          }

          const container = document.getElementById("chat-list-container");
          if (container && container.firstElementChild !== row) {
            container.prepend(row);
          }
        }
      }
    });
  }

  if (notificationsContext) {
    try {
      const wsProto = window.location.protocol === "https:" ? "wss://" : "ws://";
      const notificationSocket = new WebSocket(
        wsProto + window.location.host + "/ws/notifications/"
      );

      notificationSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        const notification = data.notification;
        
        const row = document.getElementById("friend-row-" + notification.sender_id);
        if (row) {
          const icon = row.querySelector("p i");
          if (icon) {
            icon.className = `fa-solid ${notification.type === "image" ? "fa-square text-red-500" : "fa-comment text-red-500"} fa-xs flex-shrink-0`;
          }
          const statusSpan = row.querySelector("p span:nth-of-type(1)");
          if (statusSpan) {
            statusSpan.innerText = notification.text;
            statusSpan.className = "text-red-500 font-bold truncate";
          }
          const timeSpan = row.querySelector("p span:nth-of-type(2)");
          if (timeSpan) {
            timeSpan.innerText = "Just now";
          }

          const separatorSpan = row.querySelector("p span.size-1");
          if (separatorSpan) {
            separatorSpan.style.display = "";
          }

          row.classList.add("bg-yellow-50");
          setTimeout(() => {
            row.classList.remove("bg-yellow-50");
          }, 3000);

          const container = document.getElementById("chat-list-container");
          if (container) {
            container.prepend(row);
          }
        }
      };

      notificationSocket.onclose = function(e) {
        console.warn("Notification socket closed unexpectedly.");
        startNotificationPolling();
      };
    } catch (err) {
      console.error("Failed to initialize notification socket:", err);
      startNotificationPolling();
    }
  }
});

function appendMessage(message, currentUserId) {
  const container = document.getElementById("chat-messages-container");
  if (!container) return;

  if (message.is_system) {
    const sysDiv = document.createElement("div");
    sysDiv.setAttribute("data-message-id", message.id);
    sysDiv.className = "flex justify-center my-2";
    sysDiv.innerHTML = `
      <span class="text-[10px] bg-gray-100 text-gray-500 px-3 py-1 rounded-full font-semibold border border-gray-200/50">
        ${escapeHtml(message.text)}
      </span>
    `;
    container.appendChild(sysDiv);
  } else {
    const isMe = message.sender_id === currentUserId;
    const chatDiv = document.createElement("div");
    chatDiv.setAttribute("data-message-id", message.id);
    chatDiv.className = `chat ${isMe ? "chat-end" : "chat-start"}`;

    let contentHtml = "";
    if (message.text) {
      contentHtml = `<div class="chat-bubble">${escapeHtml(message.text)}</div>`;
    } else if (message.image_url) {
      contentHtml = `
        <div class="chat-bubble p-0 max-w-24 aspect-3/4 rounded-lg overflow-hidden">
            <img src="${message.image_url}" class="w-full h-full object-cover" onload="scrollChatToBottom()">
        </div>
      `;
    }

    chatDiv.innerHTML = `
        <div class="chat-header">
            ${escapeHtml(message.sender_username)}
            <time class="text-xs opacity-50">${message.created_at}</time>
        </div>
        ${contentHtml}
    `;

    container.appendChild(chatDiv);
  }

  scrollChatToBottom();
}

function scrollChatToBottom() {
  const mainScroll = document.getElementById("chat-scroll-container");
  if (mainScroll) {
    setTimeout(() => {
      mainScroll.scrollTop = mainScroll.scrollHeight;
    }, 50);
  }
}

function showScreenshotToast(text) {
  const existing = document.getElementById("screenshot-toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.id = "screenshot-toast";
  toast.className = "absolute top-4 left-4 right-4 z-[9999] bg-black/90 backdrop-blur-md text-white text-xs font-bold py-3 px-4 rounded-xl shadow-xl flex items-center gap-2 border border-white/10 transition-all duration-300 transform -translate-y-24 opacity-0";
  toast.innerHTML = `
    <i class="fa-solid fa-camera text-red-500 animate-bounce"></i>
    <span>${escapeHtml(text)}</span>
  `;
  document.body.appendChild(toast);

  
  setTimeout(() => {
    toast.classList.remove("-translate-y-24", "opacity-0");
    toast.classList.add("translate-y-0", "opacity-100");
  }, 50);

  setTimeout(() => {
    toast.classList.remove("translate-y-0", "opacity-100");
    toast.classList.add("-translate-y-24", "opacity-0");
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4000);
}
