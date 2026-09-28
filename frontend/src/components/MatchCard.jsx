export default function MatchCard({ match, index }) {
  const level = (match.level || 'Low').toLowerCase()

  return (
    <article className={`match-card match-${level}`}>
      <div className="match-topline">
        <span>Match {index + 1}</span>
        <span className="similarity-badge">{match.similarity}% · {match.level}</span>
      </div>
      <p className="match-label">Matched text</p>
      <p className="matched-text">“{match.matched_text}”</p>
      <div className="source-block">
        <p className="match-label">Source</p>
        <strong>{match.source_title}</strong>
        <a href={match.source_url} target="_blank" rel="noreferrer">
          {match.source_url}
        </a>
        <p className="source-snippet">{match.source_snippet}</p>
      </div>
    </article>
  )
}
