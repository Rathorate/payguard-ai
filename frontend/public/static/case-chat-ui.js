const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));

export function caseChatPicker(items, currentId = '') {
  const selected = items.find(item => item.id === currentId) || items.find(item => ['OPEN','REVIEW','APPROVED'].includes(item.status)) || items[0];
  return {
    selectedId: selected?.id || '',
    options: items.length ? items.map(item => `<option value="${escape(item.id)}"${item.id === selected.id ? ' selected' : ''}>${escape(item.paypal_id)} · ${escape(item.customer)}</option>`).join('') : '<option value="">Add a case to start chatting</option>',
    empty: !items.length
  };
}
