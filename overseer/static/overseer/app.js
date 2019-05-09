var app = angular.module('myApp', ['ui-notification','ngAnimate', 'ngSanitize', 'ui.bootstrap']);

app.config(function(NotificationProvider) {
    NotificationProvider.setOptions({
        delay: 10000,
        startTop: 20,
        startRight: 10,
        verticalSpacing: 20,
        horizontalSpacing: 20,
        positionX: 'right',
        positionY: 'top'
    });
});

app.run(function($rootScope) {
    $rootScope.endpoint = 'http://poma2.creame3d.com/skynet/';
});

app.controller('PollingFilamentChangeController', function($http, $scope, $interval, $rootScope, Notification) {
    var updatedData;
    $interval(function () {
        var apiUrl = $rootScope.endpoint + 'list/pending_filament_changes/?format=json';
        return $http.get(apiUrl).then(function successCallback(response) {
            updatedData = response.data;

            $rootScope.filament_changes = updatedData;
        }, function failureCallback(reason) {
            console.log(reason);
        })
    }, 5000);

    $scope.getConfirmChange = function (id) {
        var url = $rootScope.endpoint + 'operations/confirm_filament_change/'+ id +'/';
        $http({
            method: 'PUT',
            url: url,
            data: {}
        }).then(function successCallback(response) {
            Notification({message: 'Printer ID: '+ id, title: 'Change confirmed'},'success');
        }, function errorCallback(response) {
            Notification({message: 'Error on change confirmation', title: 'Error'},'error');
        });
    }

});

app.controller('PollingPrintJobController', function($http, $scope, $interval, $rootScope, Notification) {
    var updatedData;
    $interval(function () {
        var apiUrl = $rootScope.endpoint + 'list/print_jobs_pending_for_confirmation/?format=json';
        return $http.get(apiUrl).then(function successCallback(response) {
            updatedData = response.data;
            $rootScope.print_jobs = updatedData;

        }, function failureCallback(reason) {
            console.log(reason);
        })
    }, 5000);

    $scope.PutConfirmChange = function (id, result) {
        var url = $rootScope.endpoint + 'operations/confirm_job_result/'+ id +'/';
        $http({
            method: 'PUT',
            url: url,
            data: {'success': result}
        }).then(function successCallback(response) {
            Notification({message: 'Printer ID: '+ id, title: 'Impresion cancelada'},'success');
        }, function errorCallback(response) {
            Notification({message: 'Hubo un error al intentar cancelar la impresion', title: 'Impresion cancelada'},'error');
        });
    }

});

app.controller('PollingPrintersController', function($http, $scope, $interval, $rootScope, Notification) {
    var updatedData;
    $interval(function () {
        var apiUrl = $rootScope.endpoint + 'list/printers/?format=json';
        return $http.get(apiUrl).then(function successCallback(response) {
            updatedData = response.data;

            var statusclass = 'statusclass';
            for (var i = 0; i < updatedData.length; i++) {
                // Parseamos el estado para asignarle un color en la tabla
                var status = updatedData[i];
                if (status['human_int_req'] == true) {
                    updatedData[i][statusclass] = 'table-warning';
                }
                else if (status['printer_connection_enabled'] == false){
                    updatedData[i][statusclass] = 'table-danger';
                }
                else if (status['printing'] == true) {
                    updatedData[i][statusclass] = 'table-success';
                }
                else if (status['idle'] == true) {
                    updatedData[i][statusclass] = 'table-active';
                }
                else
                {
                    updatedData[i][statusclass] = 'table-info';
                }
            }
            $rootScope.printers = updatedData;

        }, function failureCallback(reason) {
            console.log(reason);
        })
    }, 5000);

    $scope.CancelPrint = function (id, result) {
        var url = $rootScope.endpoint + 'operations/cancel_active_task/'+ id +'/';
        $http({
            method: 'GET',
            url: url
        }).then(function successCallback(response) {
            Notification({message: 'ID de impresora: '+ id, title: 'Impresion cancelada'},'success');
        }, function errorCallback(response) {
            Notification({message: 'Hubo un error al intentar cancelar la impresion', title: 'Impresion cancelada'},'error');
        });
    };

    $scope.ResetPrinter = function (id, result) {
        var url = $rootScope.endpoint + 'operations/reset_printer/'+ id +'/';
        $http({
            method: 'GET',
            url: url
        }).then(function successCallback(response) {
            Notification({message: 'ID de impresora: '+ id, title: 'Impresion cancelada'},'success');
        }, function errorCallback(response) {
            Notification({message: 'Hubo un error al intentar cancelar la impresion', title: 'Impresion cancelada'},'error');
        });
    };
});


app.filter('capitalize', function() {
    return function(input) {
        return (!!input) ? input.charAt(0).toUpperCase() + input.substr(1).toLowerCase() : '';
    }
});