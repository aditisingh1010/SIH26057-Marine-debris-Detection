import { useEffect, useState, type ReactNode } from 'react'

export default function Intro({ children }: { children: ReactNode }) {
  const [show, setShow] = useState(() => {
    try {
      return sessionStorage.getItem('sa-intro') !== '1'
    } catch {
      return true
    }
  })

  useEffect(() => {
    if (!show) return
    const t = window.setTimeout(() => {
      try {
        sessionStorage.setItem('sa-intro', '1')
      } catch {
        /* ignore */
      }
      setShow(false)
    }, 900)
    return () => window.clearTimeout(t)
  }, [show])

  return (
    <>
      {show ? (
        <div className="intro" aria-hidden="true">
          <div className="intro-wipe" />
          <p className="intro-mark">AquaX</p>
        </div>
      ) : null}
      {children}
    </>
  )
}
