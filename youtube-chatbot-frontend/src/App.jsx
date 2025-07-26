import React, { useState, useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";

const App = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

  const getVideoId = async () => {

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = new URL(tab.url);
    return new URLSearchParams(url.search).get("v");
  };

  const handleInit =  async() =>{

  const videoId = await getVideoId();
  if (!videoId) return;

  const init = await fetch("https://youtube-chatbot-jv68.onrender.com/init", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_id: videoId }),
  });

  const data = await init.json();
  if(!data.enabled)
    setMessages([{ sender: "bot", text: "This extension is not enabled for this video." }]);
  else
    setMessages([{ sender: "bot", text: "Welcome! You can ask me questions about this video." }]);
  scrollToBottom();



};

useEffect(() => {
  handleInit()
}, []);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const videoId = await getVideoId();

    const res = await fetch("https://youtube-chatbot-jv68.onrender.com/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, question: input }),
    });

    const data = await res.json();
    const botMsg = { sender: "bot", text: data.answer };
    setMessages((prev) => [...prev, botMsg]);
  };

  useEffect(scrollToBottom, [messages]);

  return (
    <div className="w-80 h-[500px] flex flex-col bg-white">
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {messages.map((msg, i) => (
          <ChatMessage key={i} {...msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="p-2 border-t flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          className="flex-1 border rounded px-2 py-1 text-sm"
          placeholder="Ask about the video..."
        />
        <button onClick={handleSend} className="bg-blue-500 text-white px-3 py-1 rounded">
          Send
        </button>
      </div>
    </div>
  );
};

export default App;
