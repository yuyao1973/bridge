"use strict";

const APP_VERSION = "v0.2.1-offline";

function pad2(n) {
  return n < 10 ? "0" + n : String(n);
}

function getBuildTime() {
  const d = new Date();
  return (
    d.getFullYear() +
    "-" +
    pad2(d.getMonth() + 1) +
    "-" +
    pad2(d.getDate()) +
    " " +
    pad2(d.getHours()) +
    ":" +
    pad2(d.getMinutes()) +
    ":" +
    pad2(d.getSeconds())
  );
}

module.exports = {
  APP_VERSION,
  getBuildTime,
};
