<?php

$variable = "hello";
$nombre = 59;
$oeuvres = [
    [
        'id' => 1,
        'titre' => 'description de oeuvre 1',
        'image' => 'lienverimage.png'
    ],
    [
        'id' => 2,
        'titre' => 'description de oeuvre 2',
        'image' => 'lienverimage.png'
    ]


];

echo $variable;

?>

<?php foreach ($oeuvres as $oeuvre) { ?>
    <?php foreach ($oeuvre as $valeur) { ?> 
        <img src="">
        <p><?php echo $valeur['titre']; ?></p>
    <?php } ?>
<?php } ?>

