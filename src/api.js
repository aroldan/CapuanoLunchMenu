const BUILDING_ID = '2392b58e-48e6-eb11-a2c9-d2abdd85801a'
const DISTRICT_ID  = '7810c14e-a7e4-eb11-a2c5-8cc0b3a2728d'
const API_URL      = 'https://api.linqconnect.com/api/FamilyMenu'

const HOT_CATEGORIES  = new Set(['hot entree', 'hot sandwich', 'breakfast entree'])
const SIDE_CATEGORIES = new Set(['side', 'vegetable'])
const ALT_CATEGORIES  = new Set(['deli', 'grab and go salad'])

export async function fetchMenu(year, month) {
  const lastDay = new Date(year, month, 0).getDate()
  const params = new URLSearchParams({
    buildingId: BUILDING_ID,
    districtId: DISTRICT_ID,
    startDate: `${month}-1-${year}`,
    endDate:   `${month}-${lastDay}-${year}`,
  })
  const resp = await fetch(`${API_URL}?${params}`)
  if (!resp.ok) throw new Error(`API returned ${resp.status}`)
  const data = await resp.json()
  return parseMenu(data, year, month)
}

function parseMenu(data, year, month) {
  const result = {}
  for (const session of data.FamilyMenuSessions ?? []) {
    if ((session.ServingSession ?? '').toLowerCase() !== 'lunch') continue
    for (const plan of session.MenuPlans ?? []) {
      for (const day of plan.Days ?? []) {
        if (!day.Date) continue
        // API returns M/D/YYYY
        const [m, d, y] = day.Date.split('/').map(Number)
        if (y !== year || m !== month) continue

        const hot = [], side = [], alt = []
        for (const meal of day.MenuMeals ?? []) {
          for (const cat of meal.RecipeCategories ?? []) {
            const catName = (cat.CategoryName ?? '').toLowerCase()
            const bucket = HOT_CATEGORIES.has(catName)  ? hot
                         : SIDE_CATEGORIES.has(catName) ? side
                         : ALT_CATEGORIES.has(catName)  ? alt
                         : null
            if (!bucket) continue
            for (const recipe of cat.Recipes ?? []) {
              const name = (recipe.RecipeName ?? '').trim()
              if (name && !bucket.includes(name)) bucket.push(name)
            }
          }
        }
        result[d] = { hot, side, alt }
      }
    }
  }
  return result
}

export function getCalendarWeeks(year, month) {
  const weeks = []
  let week = []
  const firstDow = new Date(year, month - 1, 1).getDay() // 0=Sun
  const lastDay  = new Date(year, month, 0).getDate()

  for (let i = 0; i < firstDow; i++) week.push(null)
  for (let d = 1; d <= lastDay; d++) {
    week.push(d)
    if (week.length === 7) { weeks.push(week); week = [] }
  }
  if (week.length) {
    while (week.length < 7) week.push(null)
    weeks.push(week)
  }
  return weeks
}

export function getWeekAlternates(week, menuData) {
  const alts = []
  for (let i = 1; i <= 5; i++) { // Mon–Fri only
    const day = week[i]
    if (!day) continue
    for (const a of menuData[day]?.alt ?? []) {
      if (!alts.includes(a)) alts.push(a)
    }
  }
  return alts
}
