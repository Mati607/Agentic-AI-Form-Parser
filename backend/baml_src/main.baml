client<llm> GeminiFlash {
  provider google-ai
  options {
    model "gemini-2.5-flash"
  }
}

class PassportInfo {
  last_name string?
  first_name string?
  middle_name string?
  passport_number string?
  country_of_issue string?
  nationality string?
  date_of_birth string?
  place_of_birth string?
  sex string?
  date_of_issue string?
  date_of_expiration string?
}

class AttorneyInfo {
  online_account_number string?
  family_name string?
  given_name string?
  middle_name string?
  street_number_and_name string?
  apt_ste_flr string?
  city string?
  state string?
  zip_code string?
  country string?
  daytime_telephone string?
  mobile_telephone string?
  email string?
  licensing_authority string?
  bar_number string?
  law_firm_or_organization string?
}

class ExtractedFormData {
  passport PassportInfo
  attorney AttorneyInfo
}

function ExtractPassport(doc: image) -> PassportInfo {
  client GeminiFlash
  prompt #"
    You are an expert at extracting data from passport documents (any country).
    Extract all visible fields from this passport image. Use the MRZ if present, and also any printed text.
    Return only the requested fields. Use empty string or omit if not found.
    For dates use YYYY-MM-DD when possible.
    For sex use M, F, or X.
    {{ _.role("user") }}
    Passport image: {{ doc }}
  "#
}

function ExtractG28(doc: image) -> ExtractedFormData {
  client GeminiFlash
  prompt #"
    You are an expert at extracting data from Form G-28 / Form A-28 (Attorney/Representative).
    Extract Part 1 (Attorney or Representative) into the "attorney" object and Part 3 (Passport Information for the Beneficiary) into the "passport" object.

    You MUST return a single JSON object with exactly two top-level keys: "passport" and "attorney".

    "passport" must be an object with these optional fields (use null or omit if not found): last_name, first_name, middle_name, passport_number, country_of_issue, nationality, date_of_birth, place_of_birth, sex, date_of_issue, date_of_expiration.

    "attorney" must be an object with these optional fields (use null or omit if not found): online_account_number, family_name, given_name, middle_name, street_number_and_name, apt_ste_flr, city, state, zip_code, country, daytime_telephone, mobile_telephone, email, licensing_authority, bar_number, law_firm_or_organization.

    Map form fields as follows: Part 1 attorney/representative name -> attorney.family_name, attorney.given_name, attorney.middle_name; Part 1 address -> attorney.street_number_and_name, attorney.apt_ste_flr, attorney.city, attorney.state, attorney.zip_code, attorney.country; Part 1 USCIS online account number -> attorney.online_account_number; Part 3 beneficiary passport info -> passport.*. Use YYYY-MM-DD for dates. Use M, F, or X for sex.
    {{ _.role("user") }}
    Form image: {{ doc }}
  "#
}

class DocumentValidation {
  is_valid bool
  reason string?
}

function ValidatePassport(doc: image) -> DocumentValidation {
  client GeminiFlash
  prompt #"
    Look at this document image. Determine if it is a PASSPORT (travel passport from any country).
    - Valid: ONLY passport book or passport card with MRZ, passport number, nationality, date of birth, etc. Nothing else.
    - Invalid: driver's license, national ID card, birth certificate, G-28 form, I-94, visa, or ANY other document that is not a passport. When in doubt, respond with is_valid: false.
    Respond with ONLY a single JSON object (no other text). Use exactly these keys: "is_valid" (boolean) and "reason" (string). Set is_valid to true ONLY if the document is clearly and unambiguously a passport; otherwise set is_valid to false and set reason to a brief explanation (e.g. "This appears to be a driver's license" or "This appears to be Form G-28").
    Example for invalid: {"is_valid": false, "reason": "This appears to be Form G-28."}
    Example for invalid: {"is_valid": false, "reason": "This appears to be a driver's license."}
    {{ _.role("user") }}
    Document image: {{ doc }}
  "#
}

function ValidateG28(doc: image) -> DocumentValidation {
  client GeminiFlash
  prompt #"
    Look at this document image. Determine if it is Form G-28 or Form A-28 (Notice of Entry of Appearance as Attorney or Accredited Representative).
    - Valid: USCIS Form G-28 or Form A-28 (any edition/version), even if page labels/part numbering differ or specific parts are not visible in the provided image/PDF.
    - IMPORTANT: Validate document TYPE only. Do NOT require exact section titles such as "Part 2 (Signature)" or "Part 3 (Passport info)" to mark it valid.
    - Invalid: passport, driver's license, national ID, other USCIS forms (I-485, I-130, I-94, etc.), or ANY document that is not G-28 or A-28. When in doubt, respond with is_valid: false.
    Respond with ONLY a single JSON object (no other text). Use exactly these keys: "is_valid" (boolean) and "reason" (string). Set is_valid to true ONLY if the document is clearly and unambiguously Form G-28 or Form A-28; otherwise set is_valid to false and set reason to a brief explanation (e.g. "This appears to be a passport.").
    Example for invalid: {"is_valid": false, "reason": "This appears to be a passport."}
    Example for invalid: {"is_valid": false, "reason": "This appears to be Form I-485."}
    {{ _.role("user") }}
    Document image: {{ doc }}
  "#
}
