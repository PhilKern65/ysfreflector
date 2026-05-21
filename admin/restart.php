<?php

if ($_SERVER['REQUEST_METHOD'] === 'POST') {

    $service = $_POST['service'] ?? '';

    if ($service === 'reflector') {

        // ✅ Restart YSFReflector only
        exec('pkill YSFReflector; sleep 1; cd /root/DVReflectors/YSFReflector && ./YSFReflector YSFReflector.ini > /dev/null 2>&1 &');

        echo "REFLECTOR_OK";

    } elseif ($service === 'dashboard') {

        // ✅ Restart dashboard script only
        exec('pkill -f ysf_dashboard.py; sleep 1; python3 /root/ysf_dashboard.py > /dev/null 2>&1 &');

        echo "DASHBOARD_OK";

    } else {
        echo "INVALID";
    }
}
?>
