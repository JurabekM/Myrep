# Email templates

Email templates are stored in the database (`email_templates` table) so they can
be edited from Settings → Reference data without touching the source code. The
defaults are seeded by `app/database/seed.py::seed_email_templates`.

Placeholders: {company} {company_phone} {company_email} {company_website}
{sender} {date} {buyer} {contact} {country} {quotation_number}
{quotation_total} {valid_until}
