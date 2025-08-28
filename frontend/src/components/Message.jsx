import React from 'react';

export default function Message({ role, text }) {
  const isUser = role === 'user';
  const base = 'max-w-[70%] p-3 rounded-2xl';
  const style = isUser
    ? 'bg-green-500 text-white self-end'
    : 'bg-white text-gray-800 self-start';

  return <div className={`${base} ${style}`}>{text}</div>;
}
