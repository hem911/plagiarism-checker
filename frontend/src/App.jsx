import { useState } from 'react'
import { checkPlagiarism } from './api'
import Header from './components/Header'
import InputSection from './components/InputSection'
import Results from './components/Results'
import './App.css'

const connectionError = 'Unable to reach the backend. Start Django and try again.'

export default function App() {
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [resetKey, setResetKey] = useState(0)

  const handleSubmit = async () => {
    if (!file && !text.trim()) {
      setError('Please enter text or upload a document.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const data = await checkPlagiarism(text, file)
      if (!data || data.success !== true) {
        setError(data?.error || 'The server returned an unexpected response.')
        return
      }
      setResult(data)
    } catch (requestError) {
      if (requestError.response?.data?.error) {
        setError(requestError.response.data.error)
      } else if (requestError.request) {
        setError(connectionError)
      } else {
        setError('Something went wrong while preparing your analysis.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setText('')
    setFile(null)
    setResult(null)
    setError('')
    setResetKey((key) => key + 1)
  }

  return (
    <div className="app-shell">
      <Header />
      <main>
        <section className="hero">
          <p className="eyebrow">Content similarity tool</p>
          <h1>Online Plagiarism Checker</h1>
          <p className="hero-copy">Analyze your text or document for content similarity.</p>
        </section>

        {error && <div className="error-message" role="alert">{error}</div>}

        <InputSection
          text={text}
          file={file}
          loading={loading}
          resetKey={resetKey}
          onTextChange={setText}
          onFileChange={setFile}
          onError={setError}
          onSubmit={handleSubmit}
        />

        <Results result={result} onReset={handleReset} />
      </main>
      <footer>Built for quick, local content-similarity checks.</footer>
    </div>
  )
}
