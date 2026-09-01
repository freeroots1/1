// 云函数 - 微信登录
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();
const _ = db.command;

exports.main = async (event, context) => {
  const wxContext = cloud.getWXContext();
  const { userInfo } = event;
  const openid = wxContext.OPENID;

  try {
    // 查找已有会员
    let member = await db.collection('members').where({ openid }).get();
    let memberData;

    if (member.data.length === 0) {
      // 新用户注册
      const now = db.serverDate();
      memberData = {
        openid,
        nickname: userInfo?.nickName || '微信用户',
        avatar: userInfo?.avatarUrl || '',
        level: 0,
        points: 50,
        balance: 0,
        totalSpent: 0,
        totalOrders: 0,
        lastVisit: now,
        createTime: now
      };
      const res = await db.collection('members').add({ data: memberData });
      memberData._id = res._id;
    } else {
      memberData = member.data[0];
      // 更新用户信息
      if (userInfo?.nickName) {
        await db.collection('members').doc(memberData._id).update({
          data: {
            nickname: userInfo.nickName,
            avatar: userInfo.avatarUrl || '',
            lastVisit: db.serverDate()
          }
        });
      }
    }

    const levels = ['普通会员', '金卡会员', '钻石会员'];
    const badges = ['🥉', '🥇', '💎'];
    const nextNeeds = [200, 800, 999999];

    return {
      code: 0,
      data: {
        openid,
        member: {
          id: memberData._id,
          openid: memberData.openid,
          nickname: memberData.nickname,
          avatar: memberData.avatar,
          level: memberData.level,
          levelName: levels[memberData.level] || '普通会员',
          badge: badges[memberData.level] || '🥉',
          nextLevelName: levels[memberData.level + 1] || '',
          nextNeed: nextNeeds[memberData.level] || 0,
          progress: memberData.level < 2 ? Math.min(100, Math.round((memberData.totalSpent / nextNeeds[memberData.level]) * 100)) : 100,
          points: memberData.points || 0,
          balance: memberData.balance || 0,
          totalSpent: memberData.totalSpent || 0
        }
      }
    };
  } catch (err) {
    return { code: -1, message: err.message };
  }
};
