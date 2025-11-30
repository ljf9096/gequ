<?php
$id = isset($_GET['id'])?$_GET['id']:'hnws';
$n = [
//省台
'hnws' => 145, //河南卫视
'hnds' => 141, //河南都市
'hnms' => 146, //河南民生
'hmfz' => 147, //河南法治
'hndsj' => 148, //河南电视剧
'hnxw' => 149, //河南新闻
'htgw' => 150, //欢腾购物
'hngg' => 151, //河南公共
'hnxc' => 152, //河南乡村
'hngj' => 153, //河南国际
'hnly' => 154, //河南梨园
'wwbk' => 155, //文物宝库
'wspd' => 156, //武术世界
'jczy' => 157, //睛彩中原
'ydxj' => 163, //移动戏曲
'xsj' => 183, //象视界
'gxpd' => 194, //国学频道
//地方
'zz1' => 197, //郑州新闻综合
'kf1' => 198, //开封新闻综合
'ly1' => 204, //洛阳新闻综合
'pds1' => 205, //平顶山新闻综合
'ay1' => 206, //安阳新闻综合
'hb1' => 207, //鹤壁新闻综合
'xx1' => 208, //新乡新闻综合
'jz1' => 209, //焦作新闻综合
'py1' => 219, //濮阳新闻综合
'xc1' => 220, //许昌新闻综合
'lh1' => 221, //漯河新闻综合
'smx1' => 222, //三门峡新闻综合
'ny1' => 223, //南阳新闻综合
'sq1' => 224, //商丘新闻综合
'xy1' => 225, //信阳新闻综合
'zk1' => 226, //周口新闻综合
'zmd1' => 227, //驻马店新闻综合
'jy1' => 228, //济源新闻综合
];
$t = time();
$sign = hash('sha256','6ca114a836ac7d73'.$t);
$ch = curl_init('https://pubmod.hntv.tv/program/getAuth/channel/channelIds/1/'.$n[$id]);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
curl_setopt($ch, CURLOPT_HTTPHEADER, ['timestamp:'.$t, 'sign:'.$sign,]);
$d = curl_exec($ch);
curl_close($ch);
$j = json_decode($d);
$playurl = $j[0] -> video_streams[0];
header('Location:'.$playurl);
//echo $playurl;
?>
