const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("question");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  addBubble(text, "user");
  input.value = "";
  input.disabled = true;

  try {
    const res = await fetch("http://localhost:8000/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text }),
    });

    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    const formatted = sqlFormatter.format(data.sql, { language: "mysql" });
    addBubble("```sql\n" + formatted + "\n```", "assist", true);
  } catch (err) {
    addBubble("⚠️ エラー: " + err.message, "assist");
  } finally {
    input.disabled = false;
    input.focus();
    chat.scrollTop = chat.scrollHeight;
  }
});

function addBubble(message, cls, isMarkdown = false) {
  const div = document.createElement("div");
  div.className = `bubble ${cls}`;
  div.innerHTML = isMarkdown ? renderMarkdown(message) : escapeHtml(message);
  chat.appendChild(div);
}

function escapeHtml(str) {
  return str.replace(
    /[&<>"']/g,
    (m) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[
        m
      ])
  );
}

// 最低限の ```code``` だけレンダリング
function renderMarkdown(src) {
  return src.replace(
    /```(\w+)?\n([\s\S]*?)```/g,
    (_, lang, code) => `<pre><code>${escapeHtml(code)}</code></pre>`
  );
}
