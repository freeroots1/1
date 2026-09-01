(function(root, factory) {
  var api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.YaochengCustomerEntry = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function(root) {
  'use strict';

  function hasCustomerSession(cookie) {
    return /(?:^|;\s*)yaocheng_customer_csrf=([^;]+)/.test(String(cookie || ''))
      || /(?:^|;\s*)yaocheng_csrf=([^;]+)/.test(String(cookie || ''));
  }

  function redirect(locationObject) {
    var target = locationObject || root.location;
    if (!target || target.pathname === '/modules.html' || typeof target.replace !== 'function') return false;
    target.replace('/modules.html');
    return true;
  }

  if (typeof document !== 'undefined' && !hasCustomerSession(document.cookie)) redirect(root.location);

  return { hasCustomerSession: hasCustomerSession, redirect: redirect };
});
