import './FormFillView.css'

const FORM_FILL_STORAGE_KEY_PREFIX = 'formFillData:'

const FIELDS = [
  { section: 'attorney', key: 'online_account_number', label: '1. Online Account Number' },
  { section: 'attorney', key: 'family_name', label: '2.a. Family Name (Last Name)' },
  { section: 'attorney', key: 'given_name', label: '2.b. Given Name (First Name)' },
  { section: 'attorney', key: 'middle_name', label: '2.c. Middle Name' },
  { section: 'attorney', key: 'street_number_and_name', label: '3.a. Street Number and Name' },
  { section: 'attorney', key: 'apt_ste_flr', label: 'Apt. Ste. Flr.' },
  { section: 'attorney', key: 'city', label: '3.c. City' },
  { section: 'attorney', key: 'state', label: '3.d. State' },
  { section: 'attorney', key: 'zip_code', label: '3.e. ZIP Code' },
  { section: 'attorney', key: 'country', label: '3.f. Country' },
  { section: 'attorney', key: 'daytime_telephone', label: '4. Daytime Telephone Number' },
  { section: 'attorney', key: 'mobile_telephone', label: '5. Mobile Telephone Number' },
  { section: 'attorney', key: 'email', label: '6. Email Address' },
  { section: 'attorney', key: 'licensing_authority', label: 'Licensing Authority' },
  { section: 'attorney', key: 'bar_number', label: '1.b. Bar Number' },
  { section: 'attorney', key: 'law_firm_or_organization', label: '1.d. Name of Law Firm or Organization' },
  { section: 'passport', key: 'last_name', label: '1.a. Last Name' },
  { section: 'passport', key: 'first_name', label: '1.b. First Name(s)' },
  { section: 'passport', key: 'middle_name', label: '1.c. Middle Name(s)' },
  { section: 'passport', key: 'passport_number', label: '2. Passport Number' },
  { section: 'passport', key: 'country_of_issue', label: '3. Country of Issue' },
  { section: 'passport', key: 'nationality', label: '4. Nationality' },
  { section: 'passport', key: 'date_of_birth', label: '5.a. Date of Birth' },
  { section: 'passport', key: 'place_of_birth', label: '5.b. Place of Birth' },
  { section: 'passport', key: 'sex', label: '6. Sex' },
  { section: 'passport', key: 'date_of_issue', label: '7.a. Date of Issue' },
  { section: 'passport', key: 'date_of_expiration', label: '7.b. Date of Expiration' },
]

function getValue(extracted, section, key) {
  const sec = extracted?.[section] || {}
  let v = sec[key]
  if (v == null) v = sec[key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())]
  return v != null && v !== '' ? String(v) : ''
}

export function getFormFillData(fillKey) {
  if (!fillKey) return null
  try {
    const raw = localStorage.getItem(`${FORM_FILL_STORAGE_KEY_PREFIX}${fillKey}`)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setFormFillData(extracted, form_url) {
  const key = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
  localStorage.setItem(
    `${FORM_FILL_STORAGE_KEY_PREFIX}${key}`,
    JSON.stringify({ extracted, form_url }),
  )
  return key
}

export function FormFillView() {
  const params = new URLSearchParams(window.location.search)
  const fillKey = params.get('fill_key')
  const data = getFormFillData(fillKey)
  if (!data) {
    return (
      <div className="form-fill-view">
        <p className="form-fill-error">No form data found. Use the main app to extract and fill a form first.</p>
      </div>
    )
  }

  const { extracted, form_url } = data

  const openOfficialForm = () => {
    if (form_url) window.open(form_url, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="form-fill-view">
      <header className="form-fill-header">
        <h1>Pre-filled form data</h1>
        <p>This tab shows the extracted data. It stays open so you can copy into the official form or open it below.</p>
        {form_url && (
          <button type="button" className="form-fill-open-btn" onClick={openOfficialForm}>
            Open official form in new tab
          </button>
        )}
      </header>
      <section className="form-fill-fields">
        <h2>Form A-28 – Pre-filled values</h2>
        {FIELDS.map(({ section, key, label }) => {
          const value = getValue(extracted, section, key)
          if (!value) return null
          return (
            <div key={`${section}.${key}`} className="form-fill-field">
              <label>{label}</label>
              <input type="text" value={value} readOnly />
            </div>
          )
        })}
      </section>
    </div>
  )
}
