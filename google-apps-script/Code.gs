/**
 * Early-access signups → Google Sheet + Gmail alert.
 *
 * Paste this into Extensions → Apps Script of the Google Sheet that should hold
 * your signups, then deploy it as a web app (see README.md). Every project gets
 * its own tab, named after the project's slug (e.g. "cotsi"), created on the
 * first signup.
 */

// ---- Settings -------------------------------------------------------------

// Where the "new signup" alerts go. Leave empty to use the Google account that
// owns this script (keeps your address out of the public repo).
var NOTIFY_EMAIL = '';

// Also email people who sign up with an email address ("you're on the list").
// Off by default: every email counts against Gmail's daily sending limit.
var CONFIRM_SUBSCRIBERS = false;

// Reject floods: max signups accepted per minute across all projects.
var MAX_PER_MINUTE = 60;

// ---------------------------------------------------------------------------

var HEADERS = ['Signed up', 'Name', 'Email', 'Phone', 'Source', 'Page'];
var SLUG = /^[a-z0-9]+(-[a-z0-9]+)*$/;
var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function doPost(e) {
  var p = (e && e.parameter) || {};
  try {
    if (p.website) return json_({ ok: true, status: 'added' }); // hidden field filled: a bot

    var project = clean_(p.project, 40).toLowerCase();
    var projectName = clean_(p.project_name, 60) || project;
    var email = clean_(p.email, 120).toLowerCase();
    var phone = clean_(p.phone, 30);
    var name = clean_(p.name, 80);
    var source = clean_(p.ref, 60);
    var page = clean_(p.page, 200);
    var digits = phone.replace(/\D/g, '');

    if (!SLUG.test(project)) return json_({ ok: false, error: 'Unknown project.' });
    if (!email && !phone) return json_({ ok: false, error: 'Add your email or phone number.' });
    if (email && !EMAIL.test(email)) return json_({ ok: false, error: "That email doesn't look right." });
    if (phone && (digits.length < 8 || digits.length > 15)) {
      return json_({ ok: false, error: 'Add the full phone number, with country code (like +91).' });
    }
    if (tooBusy_()) return json_({ ok: false, error: 'Lots of signups right now. Please try again in a minute.' });

    var position;
    var lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try {
      var sheet = sheetFor_(project);
      var last = sheet.getLastRow();
      var rows = last > 1 ? sheet.getRange(2, 1, last - 1, 4).getValues() : [];
      for (var i = 0; i < rows.length; i++) {
        var sameEmail = email && String(rows[i][2]).toLowerCase() === email;
        var samePhone = digits && String(rows[i][3]).replace(/\D/g, '') === digits;
        if (sameEmail || samePhone) return json_({ ok: true, status: 'exists', position: i + 1 });
      }
      sheet.appendRow([new Date(), cell_(name), cell_(email), phone ? "'" + phone : '', cell_(source), cell_(page)]);
      position = rows.length + 1;
    } finally {
      lock.releaseLock();
    }

    notify_(projectName, position, name, email, phone, source);
    if (CONFIRM_SUBSCRIBERS && email) confirm_(email, name, projectName, position);
    return json_({ ok: true, status: 'added', position: position });
  } catch (err) {
    console.error(err);
    return json_({ ok: false, error: 'Something went wrong. Please try again in a moment.' });
  }
}

// Visiting the web app URL in a browser shows this, so you can check it's live.
function doGet() {
  return json_({ ok: true, message: 'Early-access signups endpoint is running.' });
}

// Run this once from the Apps Script editor: it grants permissions and sends
// you a test alert. It adds a row to a "test" tab you can delete afterwards.
function sendTestSignup() {
  var result = doPost({ parameter: {
    project: 'test', project_name: 'Test project', email: 'test@example.com',
    name: 'Test signup', ref: 'apps-script-editor', page: 'manual test'
  } });
  console.log(result.getContent());
}

function sheetFor_(project) {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = book.getSheetByName(project);
  if (sheet) return sheet;
  sheet = book.insertSheet(project);
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]).setFontWeight('bold');
  sheet.setFrozenRows(1);
  sheet.getRange('A:A').setNumberFormat('yyyy-mm-dd hh:mm');
  return sheet;
}

function notify_(projectName, position, name, email, phone, source) {
  var lines = [
    'New early-access signup for ' + projectName + ' (#' + position + ' on the list)',
    '',
    'Name:   ' + (name || '—'),
    'Email:  ' + (email || '—'),
    'Phone:  ' + (phone || '—'),
    'Source: ' + (source || '—'),
    '',
    'All signups: ' + SpreadsheetApp.getActiveSpreadsheet().getUrl()
  ];
  var message = {
    to: NOTIFY_EMAIL || Session.getEffectiveUser().getEmail(),
    subject: '🚀 ' + projectName + ': new early-access signup (#' + position + ')',
    body: lines.join('\n'),
    name: 'Early Access'
  };
  if (email) message.replyTo = email; // hit Reply to answer them directly
  try {
    MailApp.sendEmail(message);
  } catch (err) {
    console.error('Alert email not sent (daily Gmail limit?): ' + err); // the row is still saved
  }
}

function confirm_(email, name, projectName, position) {
  try {
    MailApp.sendEmail({
      to: email,
      subject: "You're on the " + projectName + ' early-access list',
      body: 'Hi' + (name ? ' ' + name : '') + ',\n\n' +
        "You're #" + position + ' on the ' + projectName + ' list. ' +
        "I'll message you as soon as early access opens.\n\nThanks for the interest!",
      name: projectName
    });
  } catch (err) {
    console.error('Confirmation not sent: ' + err);
  }
}

function tooBusy_() {
  var cache = CacheService.getScriptCache();
  var key = 'rate:' + Math.floor(Date.now() / 60000);
  var count = Number(cache.get(key) || 0) + 1;
  cache.put(key, String(count), 120);
  return count > MAX_PER_MINUTE;
}

// A leading ' stores the value as plain text, so input like "=HYPERLINK(...)"
// can never run as a formula in your sheet.
function cell_(value) {
  return /^[=+\-@]/.test(value) ? "'" + value : value;
}

function clean_(value, max) {
  return String(value == null ? '' : value).replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max);
}

function json_(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}
