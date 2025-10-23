document.addEventListener("DOMContentLoaded", function () {
    // **HTML から `data-icon-url` を取得**
    const chatWidgetContainer = document.getElementById("chat-widget");
    const chatIconUrl = chatWidgetContainer ? chatWidgetContainer.getAttribute("data-icon-url") : "speech-bubble.png"; // デフォルト画像

    // **チャットウィジェットを作成**
    const chatWidget = document.createElement("div");
    chatWidget.innerHTML = `
        <style>
            #chat-button {
                position: fixed;
                bottom: 25px;
                right: 20px;
                background: none;
                border: none;
                width: 70px;
                height: 70px;
                cursor: pointer;
                z-index: 1000;
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.5s ease, visibility 0.5s ease, transform 0.2s ease;
            }
            #chat-button img {
                width: 100%;
                height: 100%;
                object-fit: contain;
                transition: transform 0.2s ease;
            }
            #chat-button:hover img {
                transform: scale(1.1);
            }
            #chat-container {
                position: fixed;
                bottom: 30px;
                right: 30px;
                width: 350px;
                height: 500px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.5s ease, visibility 0.5s ease;
                z-index: 1001;
            }
            #chat-container iframe {
                width: 100%;
                height: 100%;
                border: none;
            }
            #chat-close {
                position: absolute;
                top: 15px;
                right: 10px;
                width: 20px;
                height: 20px;
                background: none;
                border: none;
                cursor: pointer;
                z-index: 1002;
            }
            #chat-close::before, #chat-close::after {
                content: "";
                position: absolute;
                width: 20px;
                height: 3px;
                background-color: #666;
                top: 50%;
                left: 50%;
                transform-origin: center;
                transition: background-color 0.3s ease;
            }
            #chat-close::before {
                transform: translate(-50%, -50%) rotate(45deg);
            }
            #chat-close::after {
                transform: translate(-50%, -50%) rotate(-45deg);
            }
            #chat-close:hover::before, #chat-close:hover::after {
                background-color: #444;
            }
            .visible {
                opacity: 1 !important;
                visibility: visible !important;
            }
        </style>
        <button id="chat-button">
            <img src="${chatIconUrl}" alt="チャット">
        </button>
        <div id="chat-container">
            <button id="chat-close"></button>
            <iframe src="https://www.rnsystem.jp/message"></iframe>
        </div>
    `;
    document.body.appendChild(chatWidget);

    // **要素取得**
    const chatButton = document.getElementById("chat-button");
    const chatContainer = document.getElementById("chat-container");
    const chatClose = document.getElementById("chat-close");

    // **ページロード時にフェードイン**
    setTimeout(() => {
        chatButton.style.visibility = "visible";
        chatButton.style.opacity = "1";
    }, 500);

    // **ボタンをクリックすると、ボタンが消えてチャットが表示**
    chatButton.addEventListener("click", function () {
        chatButton.style.opacity = "0";
        setTimeout(() => chatButton.style.display = "none", 300);
        chatContainer.classList.add("visible");
    });

    // **閉じるボタンをクリックすると、チャットがフェードアウトしてボタンが復活**
    chatClose.addEventListener("click", function () {
        chatContainer.classList.remove("visible");
        setTimeout(() => {
            chatButton.style.display = "block";
            setTimeout(() => chatButton.style.opacity = "1", 10);
        }, 500);
    });
});