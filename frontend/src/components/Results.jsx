import MatchCard from './MatchCard'

export default function Results({ result, onReset }) {
  if (!result) return null

  const stats = [
    ['Words', result.total_words],
    ['Chunks', result.total_chunks],
    ['Matches', result.matches_found],
  ]

  return (
    <section className="results-section" aria-live="polite" aria-labelledby="results-heading">
      <div className="results-heading">
        <div>
          <p className="eyebrow">Analysis complete</p>
          <h2 id="results-heading">Plagiarism score</h2>
        </div>
        <button className="secondary-button" type="button" onClick={onReset}>New Analysis</button>
      </div>

      <div className="score-panel">
        <div>
          <span className="score-number">{result.plagiarism_percentage}%</span>
          <p>Similarity across the submitted content</p>
        </div>
        <div className="score-meter" aria-label={`${result.plagiarism_percentage}% similarity`}>
          <span style={{ width: `${Math.min(100, Math.max(0, result.plagiarism_percentage))}%` }} />
        </div>
      </div>

      <div className="stats-grid">
        {stats.map(([label, value]) => (
          <div className="stat-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>

      <div className="matching-content">
        <h3>Matching Content</h3>
        {result.matches_found === 0 ? (
          <p className="empty-matches">No significant matching content was found.</p>
        ) : (
          <div className="match-list">
            {result.matches.map((match, index) => <MatchCard key={`${match.source_url}-${index}`} match={match} index={index} />)}
          </div>
        )}
      </div>
    </section>
  )
}
