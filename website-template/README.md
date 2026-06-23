# Website Template

A single-page business website template with full SEO, contact modal, and GitHub Pages deployment.

## Checklist for each new site

### 1. Replace all `CAPS` placeholders in `index.html`
- `COMPANY NAME` — business name
- `TAGLINE` — short descriptor (e.g. "Inc." or "LLC")
- `CITY, STATE` — location
- `YOURDOMAIN.com` — domain
- `EMAIL@YOURDOMAIN.com` — contact email
- Hero headline, subheading, and section content
- Stats bar numbers and labels
- About section paragraphs and highlight cards
- Service card names and descriptions
- Team member initials, names, roles, and bios

### 2. Swap the color scheme (top of `index.html` `<style>`)
```css
--color-primary: #XXXXXX;  /* dominant brand color */
--color-accent:  #XXXXXX;  /* secondary/highlight  */
--color-action:  #XXXXXX;  /* CTA buttons/links    */
```

### 3. Replace `logo.png` with the actual logo file

### 4. Get a Web3Forms key for the contact form
- Go to https://web3forms.com
- Enter the destination email → click **Create Access Key**
- Replace `YOUR_WEB3FORMS_KEY` in the form's hidden input

### 5. Update `sitemap.xml` and `robots.txt`
- Replace `YOURDOMAIN.com` and `YYYY-MM-DD` in both files

### 6. Update `CNAME`
- Replace `YOURDOMAIN.com` with the actual domain

### 7. Deploy to GitHub Pages
```bash
git init
git checkout -b main
git add index.html logo.png sitemap.xml robots.txt CNAME .gitignore
git commit -m "Initial site launch"
gh repo create REPO-NAME --public --source=. --remote=origin --push
gh api repos/USERNAME/REPO-NAME/pages --method POST --field 'source[branch]=main' --field 'source[path]=/'
```

### 8. DNS records (at your registrar)
| Type  | Host | Value                        |
|-------|------|------------------------------|
| A     | @    | 185.199.108.153              |
| A     | @    | 185.199.109.153              |
| A     | @    | 185.199.110.153              |
| A     | @    | 185.199.111.153              |
| CNAME | www  | USERNAME.github.io           |

### 9. Enforce HTTPS (after DNS propagates ~30 min)
```bash
gh api repos/USERNAME/REPO-NAME/pages --method PUT --field 'cname=YOURDOMAIN.com' --field 'https_enforced=true'
```

## Branch workflow
- All changes go on `dev`
- Merge to `main` to deploy live
```bash
git checkout main && git merge dev && git push && git checkout dev
```
