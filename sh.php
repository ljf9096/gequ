<?php
error_reporting(0);
$id = $_GET['id'];
$n = [
    'dfws' => '2030', //上海东方卫视
    'xwzh' => '20', //上海新闻综合
    'xjs' => '1600', //上海新纪实
    'mdy' => '1601', //上海魔都眼
    'lypd' => '1745', //上海乐游频道
    'dycj' => '21', //上海第一财经
    'dspd' => '18', //上海都市频道
    'wxty' => '1605', //上海五星体育
];
$apiurl = 'https://bp-api.bestv.cn/cms/api/live/channels';

$context = stream_context_create([
    'ssl' => [
        'verify_peer' => false,
        'verify_peer_name' => false,
    ],
    'http' => [
        'method' => 'POST',
        'header' => "Content-Type: application/json\r\n",
        'content' => '{}'
    ]
]);

$response = file_get_contents($apiurl, false, $context);
//echo $response;
$data = json_decode($response);

foreach ($data->dt as $channel) {
    if ($channel->id == $n[$id]) {
        $playurl = $channel->channelUrl;
        break;
    }
}

header('Location: ' . $playurl);
?>