#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging
import time
import requests
import json
try:
    JSONDecodeError = json.decoder.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError

robot_token = ""  # set your robot token here
admin_mobiles = []  # set your phone number string here

def logdebug(msg, *args):
    logging.debug("DingTalkRobot " + msg, *args)


def logerror(msg, *args):
    logging.error("DingTalkRobot " + msg, *args)


class ActionCard(object):
    def __init__(self, title, text, btns=[], btn_orientation=0, hide_avatar=0):
        super(ActionCard, self).__init__()
        self.title = title  # 首屏会话透出的展示内容
        self.text = text    # markdown格式的消息
        self.btn_orientation = btn_orientation  # 0-按钮竖直排列，1-按钮横向排列
        self.hide_avatar = hide_avatar          # 0-正常发消息者头像，1-隐藏发消息者头像
        self.btns = btns    # 按钮的信息：title-按钮方案，url-点击按钮触发的URL

    def get_data(self):
        if not self.title or not self.title.strip():
            logerror("ActionCard title is empty")
            return False
        if not self.text or not self.text.strip():
            logerror("ActionCard text is empty")
            return False

        btns = []
        for btn in self.btns:
            if btn["title"] and btn["title"].strip() and btn["url"] and btn["url"].strip():
                btns.append(btn)
        if len(btns) < 1:
            logerror("ActionCard invalid btns: %s" % self.btns)
            return False

        action_card = {
            "title": self.title,
            "text": self.text,
            "hideAvatar": str(self.hide_avatar),
            "btnOrientation": str(self.btn_orientation)
        }
        if len(btns) == 1:
            # 整体跳转ActionCard类型
            action_card["singleTitle"] = btns[0]["title"]
            action_card["singleURL"] = btns[0]["actionURL"]
        else:
            links = []
            for btn in btns:
                links.append({
                    "title": btn["title"],
                    "actionURL": btn["url"]
                })
            action_card.btns = links
        data = {
            "msgtype": "actionCard",
            "actionCard": action_card
        }
        return data


class FeedCard(object):
    def __init__(self, title, message_url, pic_url):
        super(FeedCard, self).__init__()
        self.title = title
        self.message_url = message_url
        self.pic_url = pic_url

    def get_data(self):
        if not self.title or not self.title.strip():
            logerror("FeedCard title is empty")
            return False
        if not self.message_url or not self.message_url.strip():
            logerror("FeedCard message_url is empty")
            return False
        if not self.pic_url or not self.pic_url.strip():
            logerror("FeedCard pic_url is empty")
            return False

        data = {
            "title": self.title,
            "messageURL": self.message_url,
            "picURL": self.pic_url
        }
        return data


class DingTalkRobot(object):
    def __init__(self, webhook, headers={}):
        headers["Content-Type"] = "application/json"
        headers["charset"] = "utf-8"
        self.webhook = webhook
        self.headers = headers
        self.start_time = 0
        self.times = 0
        pass

    def post(self, data):
        self.times += 1
        if self.times % 20 == 0:
            past_time = time.time() - self.start_time
            if past_time < 60:
                logdebug("Send message too fast")
                time.sleep(60 - past_time)
            self.start_time = time.time()

        post_data = json.dumps(data)
        try:
            response = requests.post(self.webhook, headers=self.headers, data=post_data)
        except requests.exceptions.HTTPError as e:
            logerror("post HTTP error: %d, reason: %s" % (e.response.status_code, e.response.reason))
            raise
        except requests.exceptions.ConnectionError as e:
            logerror("post HTTP connection error! " + e)
            raise
        except requests.exceptions.Timeout:
            logerror("post request Timeout")
            raise
        except requests.exceptions.RequestException as e:
            logerror("post request exception: " + e)
            raise

        try:
            result = response.json()
        except JSONDecodeError:
            logerror("decode request error, status: %s, content: %s" % (response.status_code, response.text))
            return {'errcode': 500, 'errmsg': 'Server Error'}
        else:
            logdebug('post result: %s' % result)
            if result['errcode']:
                error_data = {
                    "msgtype": "text", "at": {"isAtAll": False, "atMobiles": admin_mobiles},
                    "text": {"content": "钉钉机器人发送消息失败，原因：%s" % result['errmsg']}
                }
                logerror("post response error: %s" % error_data)
                requests.post(self.webhook, headers=self.headers, data=json.dumps(error_data))
            return result
        pass

    def send_text(self, text, at_all=False, at_mobiles=[], at_ids=[]):
        if not text or not text.strip():
            logerror("send_text text is empty")
            return False

        data = {
            "msgtype": "text",
            "text": {
                "content": text
            },
            "at": {}
        }
        if at_all:
            data["at"]["isAtAll"] = at_all
        if at_mobiles:
            data["at"]["atMobiles"] = list(map(str, at_mobiles))
        if at_ids:
            data["at"]["atDingtalkIds"] = list(map(str, at_ids))

        logdebug('send_text: %s' % data)
        return self.post(data)

    def send_image(self, image_url):
        if not image_url or not image_url.strip():
            logerror("send_image image_url is empty")
            return False
        data = {
            "msgtype": "image",
            "image": {
                "picURL": image_url
            }
        }
        logdebug('send_image: %s' % data)
        return self.post(data)

    def send_link(self, title, text, message_url, pic_url=''):
        if not title or not title.strip():
            logerror("send_link title is empty")
            return False
        if not text or not text.strip():
            logerror("send_link text is empty")
            return False
        if not message_url or not message_url.strip():
            logerror("send_link message_url is empty")
            return False

        data = {
            "msgtype": "link",
            "link": {
                "text": text,
                "title": title,
                "picUrl": pic_url,
                "messageUrl": message_url
            }
        }
        logdebug('send_link: %s' % data)
        return self.post(data)

    def send_markdown(self, title, text, at_all=False, at_mobiles=[], at_ids=[]):
        if not title or not title.strip():
            logerror("send_markdown title is empty")
            return False
        if not text or not text.strip():
            logerror("send_markdown text is empty")
            return False

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            },
            "at": {}
        }
        if at_all:
            data["at"]["isAtAll"] = at_all
        if at_mobiles:
            data["at"]["atMobiles"] = list(map(str, at_mobiles))
        if at_ids:
            data["at"]["atDingtalkIds"] = list(map(str, at_ids))

        logging.debug("send_markdown: %s" % data)
        return self.post(data)

    def send_action_card(self, action_card):
        if not isinstance(action_card, ActionCard):
            logerror("send_action_card invalid action card: %s" % action_card)
            return False
        data = action_card.get_data()
        logdebug("send_action_card: %s" % data)
        return self.post(data)

    def send_feed_cards(self, cards):
        links = []
        for card in cards:
            if not isinstance(card, FeedCard):
                logerror("send_feed_cards invalid feed card: %s" % card)
            else:
                links.append(card.get_data())
        if not links:
            logerror("send_feed_cards no valid card")
            return False
        data = {"msgtype": "feedCard", "feedCard": {"links": links}}
        logdebug("send_feed_card: %s" % data)
        return self.post(data)


if __name__ == "__main__":
    robot = DingTalkRobot("https://oapi.dingtalk.com/robot/send?access_token=" + robot_token)
    robot.send_markdown("Hello", "This is a **markdown** format message")

