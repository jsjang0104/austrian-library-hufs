import React from 'react';

export default function ServerErrorMessage({
  message = '서버에서 정보를 불러오는데 실패했습니다.',
  germanMessage = 'Die Informationen konnten nicht vom Server geladen werden.',
}) {
  return (
    <div className="server-error-msg" role="alert">
      <p>
        <span lang="ko">{message}</span>
        <br />
        <span lang="de">{germanMessage}</span>
      </p>
      <p>
        <span lang="ko">ctrl+shift+R로 새로고침을 해주세요 (Mac에서는 command+shift+R)</span>
        <br />
        <span lang="de">Bitte laden Sie die Seite mit Strg+Umschalt+R neu (auf dem Mac mit Command+Umschalt+R).</span>
      </p>
    </div>
  );
}
