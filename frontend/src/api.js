import axios from 'axios'

const apiUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')

export async function checkPlagiarism(text, file) {
  if (file) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await axios.post(`${apiUrl}/check-plagiarism/`, formData)
    return response.data
  }

  const response = await axios.post(`${apiUrl}/check-plagiarism/`, { text })
  return response.data
}
