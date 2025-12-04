<?php

class Parser {
    private $session;
    private $cacheDir = __DIR__ . '/cache/';
    
    public function __construct() {
        $this->session = curl_init();
        curl_setopt_array($this->session, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_TIMEOUT => 10,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36',
            CURLOPT_ENCODING => 'gzip, deflate',
        ]);
        
        // 创建缓存目录
        if (!file_exists($this->cacheDir)) {
            mkdir($this->cacheDir, 0755, true);
        }
    }
    
    private function getStringMd5($s) {
        return md5($s);
    }
    
    private function getDateString($date) {
        return $date->format('Ym') . str_pad($date->format('d'), 2, '0', STR_PAD_LEFT);
    }
    
    private function getDdCalcu720p($puData, $programId) {
        $keys = "0123456789";
        $ddCalcu = [];
        
        for ($i = 0; $i < floor(strlen($puData) / 2); $i++) {
            $ddCalcu[] = $puData[strlen($puData) - $i - 1];
            $ddCalcu[] = $puData[$i];
            
            if ($i == 1) {
                $ddCalcu[] = "e";
            } elseif ($i == 2) {
                $dateStr = $this->getDateString(new DateTime());
                if (strlen($dateStr) > 6) {
                    $ddCalcu[] = $keys[intval($dateStr[6])];
                } else {
                    $ddCalcu[] = "0";
                }
            } elseif ($i == 3) {
                if (strlen($programId) > 2) {
                    $ddCalcu[] = $keys[intval($programId[2])];
                } else {
                    $ddCalcu[] = "0";
                }
            } elseif ($i == 4) {
                $ddCalcu[] = "0";
            }
        }
        
        return implode('', $ddCalcu);
    }
    
    private function getDdCalcuUrl720p($puDataUrl, $programId) {
        $urlParts = parse_url($puDataUrl);
        
        if (!isset($urlParts['query'])) {
            return $puDataUrl;
        }
        
        parse_str($urlParts['query'], $queryParams);
        
        if (!isset($queryParams['puData']) || empty($queryParams['puData'])) {
            return $puDataUrl;
        }
        
        $puData = $queryParams['puData'];
        $ddCalcu = $this->getDdCalcu720p($puData, $programId);
        $queryParams['ddCalcu'] = $ddCalcu;
        $newQuery = http_build_query($queryParams);
        
        return $urlParts['scheme'] . '://' . $urlParts['host'] . $urlParts['path'] . '?' . $newQuery;
    }
    
    private function getAndroidUrl720p($pid) {
        $timestamp = round(microtime(true) * 1000);
        $appVersion = "26000009";
        
        $headers = [
            "AppVersion: 2600000900",
            "TerminalId: android",
            "X-UP-CLIENT-CHANNEL-ID: 2600037000-99000-200300220100002",
            "Accept: application/json",
            "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
            "Connection: keep-alive"
        ];
        
        $strToHash = $timestamp . $pid . $appVersion;
        $md5Hash = $this->getStringMd5($strToHash);
        
        $salt = 66666601;
        $suffix = "770fafdf5ba04d279a59ef1600baae98migu6666";
        $sign = $this->getStringMd5($md5Hash . $suffix);
        
        $rateType = 3;
        if ($pid == "608831231") {
            $rateType = 2;
        }
        
        $baseUrl = "https://play.miguvideo.com/playurl/v1/play/playurl";
        $params = "?sign=" . $sign . "&rateType=" . $rateType . "&contId=" . $pid . "&timestamp=" . $timestamp . "&salt=" . $salt;
        $fullUrl = $baseUrl . $params;
        
        curl_setopt($this->session, CURLOPT_URL, $fullUrl);
        curl_setopt($this->session, CURLOPT_HTTPHEADER, $headers);
        
        $response = curl_exec($this->session);
        
        if (curl_errno($this->session) || !$response) {
            return null;
        }
        
        $respData = json_decode($response, true);
        
        if (!$respData) {
            return null;
        }
        
        if ((isset($respData['code']) && $respData['code'] != '200') || 
            (isset($respData['resultCode']) && $respData['resultCode'] != '200')) {
            return null;
        }
        
        if (isset($respData['data']['url'])) {
            $url = $respData['data']['url'];
        } elseif (isset($respData['body']['urlInfo']['url'])) {
            $url = $respData['body']['urlInfo']['url'];
        } elseif (isset($respData['url'])) {
            $url = $respData['url'];
        } else {
            return null;
        }
        
        if (empty($url)) {
            return null;
        }
        
        return $this->getDdCalcuUrl720p($url, $pid);
    }
    
    // 获取缓存键名
    private function getCacheKey($pid, $playseek = null) {
        return 'video_' . md5($pid . ($playseek ? '_' . $playseek : ''));
    }
    
    // 从缓存获取URL
    private function getFromCache($pid, $playseek = null) {
        $cacheFile = $this->cacheDir . $this->getCacheKey($pid, $playseek);
        
        if (file_exists($cacheFile)) {
            return file_get_contents($cacheFile);
        }
        
        return null;
    }
    
    // 保存URL到缓存
    private function saveToCache($pid, $playseek = null, $url) {
        $cacheFile = $this->cacheDir . $this->getCacheKey($pid, $playseek);
        file_put_contents($cacheFile, $url);
    }
    
    // 删除缓存
    private function deleteCache($pid, $playseek = null) {
        $cacheFile = $this->cacheDir . $this->getCacheKey($pid, $playseek);
        if (file_exists($cacheFile)) {
            unlink($cacheFile);
        }
    }
    
    // 检查URL是否有效
    private function isUrlValid($url) {
        if (empty($url)) {
            return false;
        }
        
        // 创建一个新的cURL会话来检查URL有效性
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_NOBODY => true, // 只获取头部信息，不下载内容
            CURLOPT_HEADER => true,
            CURLOPT_TIMEOUT => 5,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36',
        ]);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        // HTTP状态码为2xx或3xx表示URL有效
        return ($httpCode >= 200 && $httpCode < 400);
    }
    
    public function parse($params) {
        $pid = $params['id'] ?? "641886683";
        $playseek = $params['playseek'] ?? null;
        $forceRefresh = $params['refresh'] ?? false;
        
        // 如果强制刷新，删除缓存
        if ($forceRefresh) {
            $this->deleteCache($pid, $playseek);
        }
        
        // 尝试从缓存获取
        $cachedUrl = $this->getFromCache($pid, $playseek);
        
        if ($cachedUrl && !$forceRefresh) {
            // 检查缓存的URL是否仍然有效
            if ($this->isUrlValid($cachedUrl)) {
                return $cachedUrl;
            } else {
                // URL失效，删除缓存
                $this->deleteCache($pid, $playseek);
            }
        }
        
        // 重新获取URL
        $finalUrl = $this->getAndroidUrl720p($pid);
        
        if ($finalUrl && $playseek) {
            $parts = explode('-', $playseek);
            if (count($parts) == 2) {
                list($starttime, $endtime) = $parts;
                $separator = (strpos($finalUrl, '?') !== false) ? '&' : '?';
                $finalUrl .= $separator . "playbackbegin=" . $starttime . "&playbackend=" . $endtime;
            }
        }
        
        if ($finalUrl) {
            // 保存到缓存
            $this->saveToCache($pid, $playseek, $finalUrl);
        }
        
        return $finalUrl;
    }
    
    public function __destruct() {
        if ($this->session) {
            curl_close($this->session);
        }
    }
}

// 主程序
if (isset($_GET['id'])) {
    $parser = new Parser();
    $url = $parser->parse([
        'id' => $_GET['id'],
        'refresh' => isset($_GET['refresh']) // 可选：强制刷新参数
    ]);
    
    if ($url) {
        // 直接重定向到获取的URL
        header("Location: " . $url);
        exit;
    } else {
        http_response_code(500);
        echo "获取视频链接失败";
    }
} else {
    echo "示例: ?id=641886683<br>";
    echo "示例: ?id=641886683&refresh=1 (强制刷新缓存)";
}
