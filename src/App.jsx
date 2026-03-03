import { useState, useEffect } from 'react'
import { fetchMenu, getCalendarWeeks, getWeekAlternates } from './api'
import './App.css'

const MONTH_NAMES = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
]
const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export default function App() {
  const today = new Date()
  const [year,  setYear]  = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [menuData, setMenuData] = useState({})
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchMenu(year, month)
      .then(data => { setMenuData(data); setLoading(false) })
      .catch(err  => { setError(err.message); setLoading(false) })
  }, [year, month])

  function prevMonth() {
    if (month === 1) { setMonth(12); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }
  function nextMonth() {
    if (month === 12) { setMonth(1); setYear(y => y + 1) }
    else setMonth(m => m + 1)
  }

  const weeks = getCalendarWeeks(year, month)
  const hasAlternates = weeks.some(week =>
    week.slice(1, 6).some(day => day && menuData[day]?.alt?.length > 0)
  )

  return (
    <div className="app">
      <header className="page-header">
        <div className="header-left no-print">
          <button onClick={prevMonth} className="nav-btn" aria-label="Previous month">&#8592;</button>
          <button onClick={nextMonth} className="nav-btn" aria-label="Next month">&#8594;</button>
        </div>
        <h1>{MONTH_NAMES[month - 1]} {year} &mdash; Lunch Menu</h1>
        <button onClick={() => window.print()} className="print-btn no-print">
          Print / Save PDF
        </button>
      </header>

      {loading && <p className="status">Loading&hellip;</p>}
      {error   && <p className="status error">Error: {error}</p>}

      {!loading && !error && (
        <div className={`calendar ${hasAlternates ? 'has-alternates' : ''}`}>

          {/* Column headers */}
          <div className="cal-row header-row">
            {DAY_NAMES.map((name, i) => (
              <div key={name} className={`col-header ${i === 0 || i === 6 ? 'weekend' : ''}`}>
                {i === 0 || i === 6 ? name[0] : name}
              </div>
            ))}
            {hasAlternates && (
              <div className="col-header alt-header">Weekly Alternates</div>
            )}
          </div>

          {/* Week rows */}
          {weeks.map((week, wi) => {
            const weekAlts = getWeekAlternates(week, menuData)
            return (
              <div key={wi} className="cal-row week-row">
                {week.map((day, di) => {
                  const isWeekend = di === 0 || di === 6
                  const dayData   = day ? menuData[day] : null
                  return (
                    <div
                      key={di}
                      className={[
                        'day-cell',
                        !day        ? 'empty'   : '',
                        isWeekend   ? 'weekend' : '',
                      ].join(' ')}
                    >
                      {day && (
                        <>
                          <div className={`day-number ${isWeekend ? 'day-number--weekend' : ''}`}>
                            {day}
                          </div>
                          {!isWeekend && (
                            <div className="items">
                              {dayData?.hot?.map((item, i) => (
                                <div key={i} className="item">
                                  <span className="bullet bullet--hot">•</span>
                                  <span className="item-text">{item}</span>
                                </div>
                              ))}
                              {dayData?.side?.length > 0 && (
                                <div className="side-divider" />
                              )}
                              {dayData?.side?.map((item, i) => (
                                <div key={i} className="item item--side">
                                  <span className="bullet bullet--side">·</span>
                                  <span className="item-text">{item}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )
                })}

                {hasAlternates && (
                  <div className="alt-cell">
                    {weekAlts.map((item, i) => (
                      <div key={i} className="item item--alt">
                        <span className="bullet bullet--alt">&#9702;</span>
                        <span className="item-text">{item}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <footer className="legend no-print">
        <span className="bullet bullet--hot">•</span> Hot Entrees &nbsp;&nbsp;
        <span className="bullet bullet--side">·</span> Sides &amp; Vegetables &nbsp;&nbsp;
        <span className="bullet bullet--alt">&#9702;</span> Alternates (weekly) &nbsp;&nbsp;
        Milk and fruit not shown. &nbsp; Source: LinqConnect
      </footer>
    </div>
  )
}
