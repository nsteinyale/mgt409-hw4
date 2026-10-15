import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function CreateAccount() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [field]: e.target.value })

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.firstName.trim() || !form.lastName.trim() || !form.email.trim() || !form.password) {
      setError('Fill in every field.')
      return
    }
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) {
      setError('Enter a valid email address.')
      return
    }
    if (form.password.length < 8) {
      setError('Use at least 8 characters for your password.')
      return
    }
    // Confirm password is checked here in the browser only; the backend receives one password.
    if (form.password !== form.confirm) {
      setError("Passwords don't match.")
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await signup({ first_name: form.firstName, last_name: form.lastName, email: form.email, password: form.password })
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page auth-page">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Create account</h1>
        <p className="muted">Save your info and pick up your chats where you left off.</p>
        <div className="form-row">
          <label>
            First name
            <input value={form.firstName} onChange={update('firstName')} autoComplete="given-name" />
          </label>
          <label>
            Last name
            <input value={form.lastName} onChange={update('lastName')} autoComplete="family-name" />
          </label>
        </div>
        <label>
          Email
          <input type="email" value={form.email} onChange={update('email')} placeholder="you@yale.edu" autoComplete="email" />
        </label>
        <label>
          Password
          <input type="password" value={form.password} onChange={update('password')} autoComplete="new-password" />
        </label>
        <label>
          Confirm password
          <input type="password" value={form.confirm} onChange={update('confirm')} autoComplete="new-password" />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn btn-full" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted small">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
