
const getEl = (id) => document.getElementById(id);

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
    if (currentFile) {
      const image = ` <img
          id="preview-snap"
          src="${URL.createObjectURL(currentFile)}"
          alt="${currentFile.name}"
          class="object-cover h-full w-full"
        />`;
      previewContainer.innerHTML = image;
      caption.innerText = currentFile.name;
      previewDock.style.display = "block";
    }
  });
}

if (closePreviewBtn && snapFile && previewDock) {
  closePreviewBtn.addEventListener("click", () => {
    snapFile.value = "";
    previewDock.style.display = "none";
  });
}

if (window.location.search.includes("open=camera") && fileBtn) {
  const url = new URL(window.location);
  url.searchParams.delete('open');
  window.history.replaceState({}, document.title, url.pathname);
  fileBtn.click();
}

let callStream = null;

window.startCall = function(type) {
  const modal = getEl("calling-modal");
  const status = getEl("call-status");
  const videoContainer = getEl("video-container");
  const videoElement = getEl("call-video-preview");
  
  if (modal) {
    modal.classList.remove("hidden");
    if (status) status.innerText = "Calling...";
    
    if (type === 'video') {
      if (videoContainer) videoContainer.classList.remove("hidden");
      navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then(stream => {
          callStream = stream;
          if (videoElement) videoElement.srcObject = stream;
          if (status) status.innerText = "Connected";
        })
        .catch(err => {
          console.warn("Could not access camera/mic for call, simulating instead:", err);
          if (status) status.innerText = "Connected";
          if (videoContainer) videoContainer.classList.add("hidden");
        });
    } else {
      if (videoContainer) videoContainer.classList.add("hidden");
      setTimeout(() => {
        if (status) status.innerText = "Ringing...";
        setTimeout(() => {
          if (status) status.innerText = "Connected";
        }, 1500);
      }, 800);
    }
  }
};

window.endCall = function() {
  const modal = getEl("calling-modal");
  if (modal) {
    modal.classList.add("hidden");
  }
  if (callStream) {
    callStream.getTracks().forEach(track => track.stop());
    callStream = null;
  }
};

let activeCameraStream = null;
let capturedBlob = null;

window.openCameraModal = function() {
  const modal = getEl("camera-modal");
  const video = getEl("camera-stream");
  const fallback = getEl("camera-fallback");
  const preview = getEl("capture-preview-container");
  
  if (modal) {
    modal.classList.remove("hidden");
    if (preview) preview.classList.add("hidden");
    if (fallback) fallback.classList.add("hidden");
    const shutter = getEl("shutter-button-container");
    if (shutter) shutter.style.display = "flex";
    const header = getEl("camera-header");
    if (header) header.style.display = "flex";
    if (video) {
      video.classList.remove("hidden");
      navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false })
        .then(stream => {
          activeCameraStream = stream;
          video.srcObject = stream;
        })
        .catch(err => {
          console.warn("Camera access denied or unavailable, using fallback:", err);
          video.classList.add("hidden");
          fallback.classList.remove("hidden");
        });
    }
    
    fetchFriendsForCamera();
  }
};

window.closeCameraModal = function() {
  const modal = getEl("camera-modal");
  if (modal) modal.classList.add("hidden");
  stopActiveCamera();
};

function stopActiveCamera() {
  if (activeCameraStream) {
    activeCameraStream.getTracks().forEach(track => track.stop());
    activeCameraStream = null;
  }
}

window.triggerMockCaptureUpload = function() {
  const mockUploadInput = getEl("camera-mock-upload");
  if (mockUploadInput) mockUploadInput.click();
};

const cameraMockUpload = getEl("camera-mock-upload");
if (cameraMockUpload) {
  cameraMockUpload.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      capturedBlob = file;
      const url = URL.createObjectURL(file);
      showCapturedPreview(url);
    }
  });
}

window.capturePhoto = function() {
  const video = getEl("camera-stream");
  if (activeCameraStream && video) {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
   
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    canvas.toBlob(blob => {
      capturedBlob = new File([blob], "snap.jpg", { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);
      showCapturedPreview(url);
    }, "image/jpeg");
  } else {

    triggerMockCaptureUpload();
  }
};

function showCapturedPreview(url) {
  const preview = getEl("capture-preview-container");
  const img = getEl("captured-image-view");
  const shutter = getEl("shutter-button-container");
  if (shutter) shutter.style.display = "none";
  const header = getEl("camera-header");
  if (header) header.style.display = "none";
  if (preview && img) {
    img.src = url;
    preview.classList.remove("hidden");
    stopActiveCamera();
  }
}

window.retakePhoto = function() {
  const preview = getEl("capture-preview-container");
  if (preview) preview.classList.add("hidden");
  const shutter = getEl("shutter-button-container");
  if (shutter) shutter.style.display = "flex";
  const header = getEl("camera-header");
  if (header) header.style.display = "flex";
  openCameraModal();
};

function fetchFriendsForCamera() {
  fetch("/api/friends/")
    .then(res => res.json())
    .then(data => {
      const list = getEl("camera-friends-list");
      if (list) {
        list.innerHTML = "";
        if (!data.friends || data.friends.length === 0) {
          list.innerHTML = `<li class="p-4 text-xs text-gray-500 text-center">No friends yet. Add friends on Search!</li>`;
          return;
        }
        data.friends.forEach(friend => {
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
      }
    })
    .catch(err => console.error("Error loading friends list:", err));
}

window.sendSnapToFriend = function(friendId, username, target = "chat") {
  if (!capturedBlob) return;
  
  const formData = new FormData();
  formData.append("image", capturedBlob);
  formData.append("target", target);
  
  let csrf = "";
  const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
  if (csrfInput) {
    csrf = csrfInput.value;
  } else {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) csrf = match[1];
  }
  
  fetch(`/send-message/${friendId}`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrf
    },
    body: formData
  })
  .then(res => {
    closeCameraModal();
    alert(`Snap sent to ${username}!`);
    window.location.reload();
  })
  .catch(err => {
    console.error("Error sending snap:", err);
    alert("Failed to send snap.");
  });
};

window.sendCapturedSnapToTarget = function(target) {
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

window.postToMyStory = function() {
  if (!capturedBlob) return;
  
  const reader = new FileReader();
  reader.onloadend = function() {
    const base64data = reader.result;
    
    let stories = JSON.parse(localStorage.getItem("my_stories") || "[]");
    stories.push({
      image: base64data,
      timestamp: new Date().getTime(),
      username: "Me"
    });
    localStorage.setItem("my_stories", JSON.stringify(stories));
    
    closeCameraModal();
    alert("Snap posted to My Story!");
  };
  reader.readAsDataURL(capturedBlob);
};

let storyIndex = 0;
let storyPlayInterval = null;
let currentStoriesList = [];
const STORY_DURATION = 4000;

window.openStoriesModal = function() {
  const modal = getEl("stories-modal");
  if (!modal) return;
  
  let myStories = JSON.parse(localStorage.getItem("my_stories") || "[]");
  let friendsStories = [
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
  
  const formattedMyStories = myStories.map(s => ({
    username: "Me",
    avatar_url: "/static/snaps/default.jpg",
    image: s.image,
    time: "Just now"
  }));
  
  currentStoriesList = [...formattedMyStories, ...friendsStories];
  
  modal.classList.remove("hidden");
  storyIndex = 0;
  playStory();
};

window.closeStoriesModal = function() {
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
