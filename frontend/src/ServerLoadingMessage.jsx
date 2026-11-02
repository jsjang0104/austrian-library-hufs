import React from 'react';

export default function ServerLoadingMessage() {
  return (
    <p className="loading-msg" role="status">
      <span lang="ko">서버에서 정보를 불러오고 있습니다. 잠시만 기다려 주세요.</span>
      <br />
      <span lang="de">Die Informationen werden vom Server geladen. Bitte warten Sie einen Moment.</span>
    </p>
  );
}
