import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [text, setText] = useState('Register a synthetic patient with a unique SYN- identifier; reject duplicates.');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function generate(event) {
    event.preventDefault(); setBusy(true); setError(''); setResult(null);
    const requirements = text.split('\n').map(s => s.trim()).filter(Boolean)
      .map((text, i) => ({id: `REQ-${String(i + 1).padStart(3, '0')}`, text}));
    try {
      const response = await fetch('/api/generate', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({requirements}),
        signal: AbortSignal.timeout(60000)});
      if (!response.ok) throw new Error(response.status === 422 ?
        'Use 1–10 requirements, each 10–2000 characters long.' :
        'Generation could not complete. Check the provider configuration and try again.');
      setResult(await response.json());
    } catch (error) { setError(error.name === 'TimeoutError' ? 'Request timed out. Please try again.' : error.message); }
    finally { setBusy(false); }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'generated-test-cases.json';
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="shell">
    <header><a className="brand" href="/">QE<span> / </span>LAB</a><span className="edition">PROJECT 02 · AI-ASSISTED QA</span></header>
    <main><div className="eyebrow">FROM REQUIREMENTS TO REVIEWABLE COVERAGE</div>
      <h1>Build a better<br/><span>first test draft.</span></h1>
      <p className="intro">Turn acceptance criteria into traceable positive, negative, and boundary cases. Review every result before it enters your suite.</p>
      <div className="workspace"><section className="input-panel">
        <div className="panel-heading"><span className="number">01</span><h2>Define the requirements</h2></div>
        <form onSubmit={generate}><label htmlFor="requirements">Acceptance criteria</label>
          <p id="help" className="help">One requirement per line · Up to 10 · Synthetic data only</p>
          <textarea id="requirements" aria-describedby="help" rows="9" required value={text} onChange={e => setText(e.target.value)}/>
          <button className="primary" disabled={busy}>{busy ? 'Generating…' : 'Generate test cases →'}</button>
        </form>
        <p className="note">Offline demo uses deterministic templates. OpenAI or FreeLLMAPI must be explicitly configured on the server.</p>
      </section><section className="results" aria-busy={busy}>
        <div className="panel-heading"><span className="number">02</span><h2>Review the coverage</h2></div>
        {error && <p role="alert" className="error">{error}</p>}
        <p role="status" className="status">{busy ? 'Preparing your draft…' : result ? `${result.suite.cases.length} draft cases · ${result.provider} · Human review required` : 'Your generated cases will appear here.'}</p>
        {!result && !busy && <div className="empty"><span>↗</span><h3>A clear requirement is a strong start.</h3><p>Each case links back to its source and includes steps, expected results, and priority.</p></div>}
        {result && <><button className="export" onClick={download}>Export JSON ↓</button><div className="cases">{result.suite.cases.map(c => <article key={c.id} className="case">
          <div className="tags"><span>{c.requirement_id}</span><span className={c.category}>{c.category}</span><span>{c.priority}</span></div>
          <h3>{c.title}</h3><details><summary>Steps & expected result</summary><h4>Preconditions</h4><ul>{c.preconditions.map((s,i)=><li key={i}>{s}</li>)}</ul><ol>{c.steps.map((s,i)=><li key={i}>{s}</li>)}</ol><p><strong>Expected:</strong> {c.expected_result}</p></details>
        </article>)}</div></>}
      </section></div>
    </main><footer>SOFTWARE QUALITY ENGINEERING PORTFOLIO <span>Traceability starts here.</span></footer>
  </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
