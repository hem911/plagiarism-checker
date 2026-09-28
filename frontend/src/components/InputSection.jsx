const ALLOWED_EXTENSIONS = ['txt', 'pdf', 'docx']

export default function InputSection({
  text,
  file,
  loading,
  resetKey,
  onTextChange,
  onFileChange,
  onError,
  onSubmit,
}) {
  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) return

    const extension = selectedFile.name.split('.').pop().toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      onFileChange(null)
      onError('Please choose a TXT, PDF, or DOCX document.')
      return
    }

    onError('')
    onFileChange(selectedFile)
  }

  return (
    <section className="input-card" aria-labelledby="input-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">New analysis</p>
          <h2 id="input-heading">Check your content</h2>
        </div>
        <span className="supported-files">TXT · PDF · DOCX</span>
      </div>

      <label className="field-label" htmlFor="analysis-text">Paste text</label>
      <textarea
        id="analysis-text"
        value={text}
        onChange={(event) => onTextChange(event.target.value)}
        placeholder="Paste your text here..."
        disabled={loading}
        rows="9"
      />

      <div className="upload-row">
        <div>
          <span className="field-label">Or upload a document</span>
          <p className="field-help">Uploaded files take priority when both options are filled.</p>
        </div>
        <label className="file-picker">
          <input
            key={resetKey}
            type="file"
            accept=".txt,.pdf,.docx"
            onChange={handleFileChange}
            disabled={loading}
          />
          <span>Choose file</span>
        </label>
      </div>

      {file && <p className="selected-file">Selected: <strong>{file.name}</strong></p>}

      <button className="primary-button" type="button" onClick={onSubmit} disabled={loading}>
        {loading ? 'Analyzing...' : 'Check Plagiarism'}
      </button>
    </section>
  )
}
