"use strict";
const assert = require("node:assert/strict");
function ok(condizione, messaggio) {
  assert.ok(condizione, messaggio);
  console.log("OK   " + messaggio);
}
module.exports = { ok };
