import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [sessionId, setSessionId] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const uploadPdf = async () => {
    if (!file) {
      alert("Please select PDF");
      return;
    }

    const formData = new FormData();

    formData.append("file", file);

    setLoading(true);

    const response = await fetch(
      "http://127.0.0.1:8000/upload",
      {
        method: "POST",
        body: formData,
      }
    );

    const data = await response.json();

    setSessionId(data.session_id);

    setLoading(false);

    alert("PDF uploaded successfully");
  };

  const askQuestion = async () => {
    if (!sessionId) {
      alert("Upload PDF first");
      return;
    }

    setLoading(true);

    const response = await fetch(
      "http://127.0.0.1:8000/query",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          question: question,
        }),
      }
    );

    const data = await response.json();

    setAnswer(data.answer);

    setLoading(false);
  };

  return (
    <div style={{ padding: "40px" }}>
      <h1>PDF RAG Query App</h1>

      <input
        type="file"
        accept=".pdf"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <br />
      <br />

      <button onClick={uploadPdf}>
        Upload PDF
      </button>

      <br />
      <br />

      <textarea
        rows="5"
        cols="60"
        placeholder="Ask question about PDF..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />

      <br />
      <br />

      <button onClick={askQuestion}>
        Ask Question
      </button>

      {loading && <p>Loading...</p>}

      <h3>Answer:</h3>

      <p>{answer}</p>
    </div>
  );
}

export default App;